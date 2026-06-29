"""In-TUI settings screen."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
)

from sybl.hotkeys.bindings import BindingParseError, parse_binding
from sybl.tui.sound_picker import browse_wav_file

_BUILTIN_SOUND = "builtin"


class SettingsScreen(ModalScreen[None]):
    BINDINGS = [("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(
            "Settings (changes apply immediately via daemon)",
            id="settings-title",
        )
        with Vertical(id="settings-form"):
            yield Label("Preferred provider")
            yield Select(
                [("groq", "groq"), ("deepgram", "deepgram")],
                id="provider-select",
            )
            yield Label("Provider API key")
            with Vertical(classes="key-row"):
                yield Select(
                    [("groq", "groq"), ("deepgram", "deepgram")],
                    id="key-provider-select",
                )
                yield Input(placeholder="Paste API key", password=True, id="key-input")
                yield Button("Save key", id="save-key-btn", variant="primary")
            yield Label("Hotkey mode")
            yield Select(
                [("both", "both"), ("ptt", "ptt"), ("toggle", "toggle")],
                id="hotkey-mode-select",
            )
            yield Label("Hotkey binding (e.g. ctrl+alt+space)")
            yield Input(id="hotkey-binding")
            yield Label("Cancel binding (e.g. esc)")
            yield Input(id="hotkey-cancel-binding")
            yield Label("Toggle double-press window (ms)")
            yield Input(id="hotkey-toggle-ms", value="400")
            yield Button("Save hotkey", id="save-hotkey-btn", variant="primary")
            yield Label("Sound cues folder")
            yield Static("", id="sounds-dir")
            yield Checkbox("Indicator sound cue", id="indicator-sound-enabled")
            yield Label("Volume (0-100)")
            yield Input(id="sound-volume", value="75")
            yield Label("Start cue")
            with Horizontal():
                yield Select(
                    [("Built-in chime", _BUILTIN_SOUND)],
                    id="sound-start-select",
                )
                yield Button("Browse…", id="browse-start-sound")
                yield Button("Built-in", id="clear-start-sound")
            yield Label("Stop cue")
            with Horizontal():
                yield Select(
                    [("Built-in chime", _BUILTIN_SOUND)],
                    id="sound-stop-select",
                )
                yield Button("Browse…", id="browse-stop-sound")
                yield Button("Built-in", id="clear-stop-sound")
            yield Label("Import from path (paste a .wav path below)")
            yield Input(
                id="sound-import-path",
                placeholder=r"C:\path\to\cue.wav",
            )
            with Horizontal():
                yield Select(
                    [("start", "Start cue"), ("stop", "Stop cue")],
                    id="sound-import-role",
                )
                yield Button("Import path", id="import-sound-path-btn")
            yield Button("Save sound settings", id="save-sound-btn", variant="primary")
            yield Checkbox("Injection enabled", id="inject-enabled")
            yield Checkbox("Post-process enabled", id="postprocess-enabled")
            yield Checkbox("Trim filler words", id="trim-fillers")
            yield Checkbox("Capitalize first letter", id="capitalize")
            yield Checkbox("Ensure punctuation", id="ensure-punctuation")
            yield Checkbox("Collapse repeated words", id="collapse-repeated")
            yield Checkbox("Normalize quotes/dashes", id="normalize-quotes")
            yield Checkbox(
                "Trim space before punctuation",
                id="trim-punct-space",
            )
            yield Checkbox("Voice commands enabled", id="voice-commands-enabled")
            yield Static("", id="settings-status")
        yield Footer()

    async def on_mount(self) -> None:
        config = await self.app.ipc.get_config()
        provider = config.get("provider", {})
        if isinstance(provider, dict):
            preferred = str(provider.get("preferred", "groq"))
            self.query_one("#provider-select", Select).value = preferred
        hotkey = config.get("hotkey", {})
        if isinstance(hotkey, dict):
            self.query_one("#hotkey-mode-select", Select).value = str(
                hotkey.get("mode", "both")
            )
            self.query_one("#hotkey-binding", Input).value = str(
                hotkey.get("binding", "ctrl+alt+space")
            )
            self.query_one("#hotkey-cancel-binding", Input).value = str(
                hotkey.get("cancel_binding", "esc")
            )
            self.query_one("#hotkey-toggle-ms", Input).value = str(
                hotkey.get("toggle_double_press_ms", 400)
            )
        indicator = config.get("indicator", {})
        if isinstance(indicator, dict):
            self.query_one("#indicator-sound-enabled", Checkbox).value = bool(
                indicator.get("sound_enabled", False)
            )
            volume = float(indicator.get("sound_volume", 0.75))
            self.query_one("#sound-volume", Input).value = str(int(round(volume * 100)))
        inject = config.get("inject", {})
        if isinstance(inject, dict):
            self.query_one("#inject-enabled", Checkbox).value = bool(
                inject.get("enabled", True)
            )
        postprocess = config.get("postprocess", {})
        if isinstance(postprocess, dict):
            self.query_one("#postprocess-enabled", Checkbox).value = bool(
                postprocess.get("enabled", True)
            )
            self.query_one("#trim-fillers", Checkbox).value = bool(
                postprocess.get("trim_fillers", True)
            )
            self.query_one("#capitalize", Checkbox).value = bool(
                postprocess.get("capitalize", True)
            )
            self.query_one("#ensure-punctuation", Checkbox).value = bool(
                postprocess.get("ensure_punctuation", False)
            )
            self.query_one("#collapse-repeated", Checkbox).value = bool(
                postprocess.get("collapse_repeated_words", False)
            )
            self.query_one("#normalize-quotes", Checkbox).value = bool(
                postprocess.get("normalize_quotes", True)
            )
            self.query_one("#trim-punct-space", Checkbox).value = bool(
                postprocess.get("trim_space_before_punctuation", True)
            )
        voice_commands = config.get("voice_commands", {})
        if isinstance(voice_commands, dict):
            self.query_one("#voice-commands-enabled", Checkbox).value = bool(
                voice_commands.get("enabled", True)
            )
        await self._refresh_sound_controls()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "save-key-btn":
            await self._save_key()
        elif button_id == "save-hotkey-btn":
            await self._save_hotkey()
        elif button_id == "save-sound-btn":
            await self._save_sound_settings()
        elif button_id == "browse-start-sound":
            await self._browse_and_import("start")
        elif button_id == "browse-stop-sound":
            await self._browse_and_import("stop")
        elif button_id == "clear-start-sound":
            await self._use_builtin_sound("start")
        elif button_id == "clear-stop-sound":
            await self._use_builtin_sound("stop")
        elif button_id == "import-sound-path-btn":
            await self._import_sound_from_path()

    async def _save_key(self) -> None:
        provider_select = self.query_one("#key-provider-select", Select)
        key_input = self.query_one("#key-input", Input)
        provider = str(provider_select.value or "groq")
        key = key_input.value.strip()
        if not key:
            self._set_status("Enter an API key first.")
            return
        await self.app.ipc.set_provider_key(provider, key)
        key_input.value = ""
        self._set_status(f"Saved key for {provider}.")

    async def _save_hotkey(self) -> None:
        binding = self.query_one("#hotkey-binding", Input).value.strip()
        cancel = self.query_one("#hotkey-cancel-binding", Input).value.strip()
        mode = str(self.query_one("#hotkey-mode-select", Select).value or "ptt")
        toggle_ms_raw = self.query_one("#hotkey-toggle-ms", Input).value.strip()
        try:
            parse_binding(binding)
            parse_binding(cancel)
        except BindingParseError as exc:
            self._set_status(f"Invalid binding: {exc}")
            return
        try:
            toggle_ms = int(toggle_ms_raw)
        except ValueError:
            self._set_status("Toggle window must be an integer (200-1000 ms).")
            return
        if toggle_ms < 200 or toggle_ms > 1000:
            self._set_status("Toggle window must be between 200 and 1000 ms.")
            return
        await self.app.ipc.patch_config(
            {
                "hotkey": {
                    "mode": mode,
                    "binding": binding,
                    "cancel_binding": cancel,
                    "toggle_double_press_ms": toggle_ms,
                }
            }
        )
        self._set_status("Hotkey settings saved.")
        await self.app.refresh_dashboard()

    async def _save_sound_settings(self) -> None:
        volume_raw = self.query_one("#sound-volume", Input).value.strip()
        try:
            volume_pct = int(volume_raw)
        except ValueError:
            self._set_status("Volume must be an integer from 0 to 100.")
            return
        if volume_pct < 0 or volume_pct > 100:
            self._set_status("Volume must be between 0 and 100.")
            return

        start_value = str(self.query_one("#sound-start-select", Select).value)
        stop_value = str(self.query_one("#sound-stop-select", Select).value)
        indicator_patch: dict = {
            "sound_enabled": self.query_one(
                "#indicator-sound-enabled",
                Checkbox,
            ).value,
            "sound_volume": volume_pct / 100.0,
        }
        if start_value != _BUILTIN_SOUND:
            indicator_patch["sound_start_file"] = start_value
        if stop_value != _BUILTIN_SOUND:
            indicator_patch["sound_stop_file"] = stop_value
        await self.app.ipc.patch_config({"indicator": indicator_patch})
        if start_value == _BUILTIN_SOUND:
            await self.app.ipc.clear_sound("start")
        if stop_value == _BUILTIN_SOUND:
            await self.app.ipc.clear_sound("stop")
        self._set_status("Sound settings saved.")
        await self._refresh_sound_controls()
        await self.app.refresh_dashboard()

    async def _browse_and_import(self, role: str) -> None:
        selected = await asyncio.to_thread(
            browse_wav_file,
            title=f"Select {role} sound cue",
        )
        if selected is None:
            self._set_status("Browse cancelled or unavailable on this platform.")
            return
        await self._import_sound_file(role, selected)

    async def _import_sound_from_path(self) -> None:
        raw_path = self.query_one("#sound-import-path", Input).value.strip()
        role = str(self.query_one("#sound-import-role", Select).value or "start")
        if not raw_path:
            self._set_status("Paste a .wav file path to import.")
            return
        await self._import_sound_file(role, Path(raw_path))

    async def _import_sound_file(self, role: str, path: Path) -> None:
        try:
            await self.app.ipc.import_sound(role, str(path))
        except Exception as exc:
            self._set_status(f"Import failed: {exc}")
            return
        self.query_one("#sound-import-path", Input).value = ""
        self._set_status(f"Imported {path.name} as {role} cue.")
        await self._refresh_sound_controls()
        await self.app.refresh_dashboard()

    async def _use_builtin_sound(self, role: str) -> None:
        await self.app.ipc.clear_sound(role)
        key = "sound_start_file" if role == "start" else "sound_stop_file"
        await self.app.ipc.patch_config({"indicator": {key: None}})
        self._set_status(f"Using built-in chime for {role}.")
        await self._refresh_sound_controls()
        await self.app.refresh_dashboard()

    async def _refresh_sound_controls(self) -> None:
        try:
            payload = await self.app.ipc.list_sounds()
        except Exception:
            self._set_status("Could not load sound cue list from daemon.")
            return

        sounds_dir = str(payload.get("sounds_dir", ""))
        self.query_one("#sounds-dir", Static).update(sounds_dir or "(unknown)")
        files = payload.get("files", [])
        options: list[tuple[str, str]] = [("Built-in chime", _BUILTIN_SOUND)]
        if isinstance(files, list):
            options.extend((name, name) for name in files if isinstance(name, str))

        self._apply_sound_select(
            "#sound-start-select",
            options,
            payload.get("start_file"),
        )
        self._apply_sound_select(
            "#sound-stop-select",
            options,
            payload.get("stop_file"),
        )

    def _apply_sound_select(
        self,
        selector: str,
        options: list[tuple[str, str]],
        configured: object,
    ) -> None:
        select = self.query_one(selector, Select)
        select.set_options(options)
        legal = {value for _, value in options}
        if isinstance(configured, str) and configured in legal:
            select.value = configured
        elif _BUILTIN_SOUND in legal:
            select.value = _BUILTIN_SOUND

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "provider-select":
            provider = str(event.value or "groq")
            await self.app.ipc.patch_config({"provider": {"preferred": provider}})
            self._set_status(f"Preferred provider set to {provider}.")
            await self.app.refresh_dashboard()
            return
        if event.select.id in ("sound-start-select", "sound-stop-select"):
            return

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        patch: dict = {}
        if event.checkbox.id == "indicator-sound-enabled":
            patch = {"indicator": {"sound_enabled": event.value}}
        elif event.checkbox.id == "inject-enabled":
            patch = {"inject": {"enabled": event.value}}
        elif event.checkbox.id == "postprocess-enabled":
            patch = {"postprocess": {"enabled": event.value}}
        elif event.checkbox.id == "trim-fillers":
            patch = {"postprocess": {"trim_fillers": event.value}}
        elif event.checkbox.id == "capitalize":
            patch = {"postprocess": {"capitalize": event.value}}
        elif event.checkbox.id == "ensure-punctuation":
            patch = {"postprocess": {"ensure_punctuation": event.value}}
        elif event.checkbox.id == "collapse-repeated":
            patch = {"postprocess": {"collapse_repeated_words": event.value}}
        elif event.checkbox.id == "normalize-quotes":
            patch = {"postprocess": {"normalize_quotes": event.value}}
        elif event.checkbox.id == "trim-punct-space":
            patch = {"postprocess": {"trim_space_before_punctuation": event.value}}
        elif event.checkbox.id == "voice-commands-enabled":
            patch = {"voice_commands": {"enabled": event.value}}
        else:
            return
        await self.app.ipc.patch_config(patch)
        self._set_status("Updated configuration.")
        await self.app.refresh_dashboard()

    def _set_status(self, message: str) -> None:
        self.query_one("#settings-status", Static).update(message)
