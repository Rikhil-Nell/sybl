"""Async IPC servers for daemon command and event channels."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from navi.ipc.protocol import (
    CommandName,
    CommandResponse,
    encode_line,
    parse_command_request,
    parse_event_hello,
)

logger = logging.getLogger("navi.ipc.server")

CommandHandler = Callable[[CommandName, dict[str, Any]], Awaitable[dict[str, Any]]]


class IpcServer:
    def __init__(
        self,
        *,
        host: str,
        command_port: int,
        event_port: int,
        token: str,
        command_handler: CommandHandler,
    ) -> None:
        self._host = host
        self._command_port = command_port
        self._event_port = event_port
        self._token = token
        self._command_handler = command_handler
        self._command_server: asyncio.Server | None = None
        self._event_server: asyncio.Server | None = None
        self._event_clients: set[asyncio.StreamWriter] = set()
        self._event_clients_lock = asyncio.Lock()

    @property
    def command_port(self) -> int:
        if self._command_server is None:
            return self._command_port
        for sock in self._command_server.sockets or []:
            return sock.getsockname()[1]
        return self._command_port

    @property
    def event_port(self) -> int:
        if self._event_server is None:
            return self._event_port
        for sock in self._event_server.sockets or []:
            return sock.getsockname()[1]
        return self._event_port

    async def start(self) -> None:
        self._command_server = await asyncio.start_server(
            self._handle_command_client,
            self._host,
            self._command_port,
        )
        self._event_server = await asyncio.start_server(
            self._handle_event_client,
            self._host,
            self._event_port,
        )
        cmd_port = self.command_port
        evt_port = self.event_port
        logger.info(
            "IPC listening on %s (command=%s, events=%s)",
            self._host,
            cmd_port,
            evt_port,
        )

    async def stop(self) -> None:
        async with self._event_clients_lock:
            for writer in list(self._event_clients):
                writer.close()
            self._event_clients.clear()

        if self._command_server is not None:
            self._command_server.close()
            await self._command_server.wait_closed()
            self._command_server = None

        if self._event_server is not None:
            self._event_server.close()
            await self._event_server.wait_closed()
            self._event_server = None

    async def broadcast_event(self, payload: dict[str, Any]) -> None:
        line = encode_line(payload)
        async with self._event_clients_lock:
            dead: list[asyncio.StreamWriter] = []
            for writer in self._event_clients:
                try:
                    writer.write(line)
                    await writer.drain()
                except Exception:
                    dead.append(writer)
            for writer in dead:
                self._event_clients.discard(writer)
                writer.close()

    async def _handle_command_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername")
        try:
            line = await reader.readline()
            if not line:
                return
            try:
                request = parse_command_request(line)
            except ValueError as exc:
                response = CommandResponse(
                    id="",
                    ok=False,
                    error=str(exc),
                )
                writer.write(encode_line(response.model_dump(mode="json")))
                await writer.drain()
                return

            try:
                result = await self._command_handler(request.command, request.params)
                response = CommandResponse(id=request.id, ok=True, result=result)
            except Exception as exc:
                logger.exception("Command %s failed", request.command)
                response = CommandResponse(id=request.id, ok=False, error=str(exc))

            writer.write(encode_line(response.model_dump(mode="json")))
            await writer.drain()
        except Exception:
            logger.exception("Command client error from %s", peer)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_event_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername")
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=10.0)
            if not line:
                return
            try:
                hello = parse_event_hello(line)
            except ValueError:
                writer.close()
                return
            if hello.token != self._token:
                logger.warning("Rejected event client from %s (bad token)", peer)
                writer.close()
                return

            writer.write(encode_line({"type": "subscribed"}))
            await writer.drain()

            async with self._event_clients_lock:
                self._event_clients.add(writer)

            while True:
                if reader.at_eof():
                    break
                data = await reader.read(1024)
                if not data:
                    break
        except TimeoutError:
            logger.debug("Event client hello timeout from %s", peer)
        except Exception:
            logger.exception("Event client error from %s", peer)
        finally:
            async with self._event_clients_lock:
                self._event_clients.discard(writer)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
