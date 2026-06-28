"""In-TUI settings screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
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
                [( "groq", "groq"), ("deepgram", "deepgram")],
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
            yield Checkbox("Injection enabled", id="inject-enabled")
            yield Checkbox("Post-process enabled", id="postprocess-enabled")
            yield Checkbox("Trim filler words", id="trim-fillers")
            yield Checkbox("Capitalize first letter", id="capitalize")
            yield Checkbox("Ensure punctuation", id="ensure-punctuation")
            yield Static("", id="settings-status")
        yield Footer()

    async def on_mount(self) -> None:
        config = await self.app.ipc.get_config()
        provider = config.get("provider", {})
        if isinstance(provider, dict):
            preferred = str(provider.get("preferred", "groq"))
            self.query_one("#provider-select", Select).value = preferred
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

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "save-key-btn":
            return
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

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "provider-select":
            return
        provider = str(event.value or "groq")
        await self.app.ipc.patch_config({"provider": {"preferred": provider}})
        self._set_status(f"Preferred provider set to {provider}.")
        await self.app.refresh_dashboard()

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        patch: dict = {}
        if event.checkbox.id == "inject-enabled":
            patch = {"inject": {"enabled": event.value}}
        elif event.checkbox.id == "postprocess-enabled":
            patch = {"postprocess": {"enabled": event.value}}
        elif event.checkbox.id == "trim-fillers":
            patch = {"postprocess": {"trim_fillers": event.value}}
        elif event.checkbox.id == "capitalize":
            patch = {"postprocess": {"capitalize": event.value}}
        elif event.checkbox.id == "ensure-punctuation":
            patch = {"postprocess": {"ensure_punctuation": event.value}}
        else:
            return
        await self.app.ipc.patch_config(patch)
        self._set_status("Updated configuration.")
        await self.app.refresh_dashboard()

    def _set_status(self, message: str) -> None:
        self.query_one("#settings-status", Static).update(message)
