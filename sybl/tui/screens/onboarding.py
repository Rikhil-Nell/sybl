"""First-run BYOK onboarding wizard."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static


class OnboardingScreen(ModalScreen[bool]):
    BINDINGS = [("escape", "skip", "Skip")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Welcome to sybl", id="onboarding-title")
        with Vertical(id="onboarding-body"):
            yield Static(
                "sybl is bring-your-own-key dictation. "
                "Add an API key for your STT provider to get started."
            )
            yield Label("Choose a provider")
            yield Select(
                [("groq", "groq"), ("deepgram", "deepgram")],
                id="onboarding-provider",
            )
            yield Label("API key")
            yield Input(placeholder="Paste API key", password=True, id="onboarding-key")
            yield Static("", id="onboarding-status")
            yield Button("Save and continue", id="onboarding-save", variant="primary")
            yield Button("Skip for now", id="onboarding-skip")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "onboarding-skip":
            self.dismiss(False)
            return
        if event.button.id != "onboarding-save":
            return
        provider = str(self.query_one("#onboarding-provider", Select).value or "groq")
        key = self.query_one("#onboarding-key", Input).value.strip()
        if not key:
            self.query_one("#onboarding-status", Static).update("Enter an API key.")
            return
        await self.app.ipc.set_provider_key(provider, key)
        await self.app.ipc.patch_config(
            {
                "provider": {"preferred": provider},
                "ui": {"onboarding_complete": True},
            }
        )
        self.dismiss(True)

    def action_skip(self) -> None:
        self.dismiss(False)
