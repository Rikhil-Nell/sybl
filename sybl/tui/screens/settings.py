"""In-TUI settings modal with sidebar sections."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    ContentSwitcher,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
)

from sybl.hotkeys.bindings import BindingParseError, parse_binding
from sybl.tui.sound_picker import browse_wav_file

_BUILTIN_SOUND = "builtin"

_SECTIONS: list[tuple[str, str]] = [
    ("provider", "Provider"),
    ("hotkey", "Hotkey"),
    ("audio", "Audio"),
    ("indicator", "Indicator"),
    ("injection", "Injection"),
    ("text", "Text"),
    ("advanced", "Advanced"),
]

# Per-section heading + one-line description shown above each form.
_SECTION_META: dict[str, tuple[str, str]] = {
    "provider": (
        "Provider",
        "Which BYOK speech-to-text service transcribes you, and its models.",
    ),
    "hotkey": (
        "Hotkey",
        "How you trigger and cancel dictation.",
    ),
    "audio": (
        "Audio",
        "Microphone input and capture options.",
    ),
    "indicator": (
        "Indicator",
        "The on-screen listening pill and its sound cues.",
    ),
    "injection": (
        "Injection",
        "How transcribed text is typed into the focused app.",
    ),
    "text": (
        "Text",
        "Post-processing, voice commands, and vocabulary hints.",
    ),
    "advanced": (
        "Advanced",
        "Logging and history sizes.",
    ),
}


class SettingsScreen(ModalScreen[None]):
    BINDINGS = [("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-modal"):
            with Vertical(id="settings-header"):
                yield Static("Settings", id="settings-title")
                yield Static(
                    "Changes apply via daemon immediately",
                    id="settings-subtitle",
                )
            with Horizontal(id="settings-body"):
                with Vertical(id="settings-nav"):
                    yield Static("SECTIONS", id="settings-nav-title")
                    yield ListView(
                        *[
                            ListItem(Static(label, id=f"nav-{key}"))
                            for key, label in _SECTIONS
                        ],
                        id="settings-nav-list",
                    )
                with ContentSwitcher(initial="provider", id="settings-content"):
                    yield from self._provider_section()
                    yield from self._hotkey_section()
                    yield from self._audio_section()
                    yield from self._indicator_section()
                    yield from self._injection_section()
                    yield from self._text_section()
                    yield from self._advanced_section()
            yield Static("", id="settings-status")
            yield Static(
                "Esc back  ·  ↑↓ switch section  ·  edit raw file with e on the "
                "dashboard",
                id="settings-footer",
            )

    def _head(self, key: str) -> ComposeResult:
        title, desc = _SECTION_META[key]
        yield Static(title, classes="section-head")
        yield Static(desc, classes="section-desc")

    def _provider_section(self) -> ComposeResult:
        with Vertical(id="provider", classes="settings-section"):
            yield from self._head("provider")
            yield Label("Preferred provider")
            yield Select(
                [("groq", "groq"), ("deepgram", "deepgram")],
                id="provider-select",
            )
            yield Label("Fallback order (comma-separated)")
            yield Input(id="provider-fallback", placeholder="deepgram, groq")
            yield Label("Groq model")
            yield Input(id="groq-model", placeholder="whisper-large-v3-turbo")
            yield Label("Deepgram model")
            yield Input(id="deepgram-model", placeholder="nova-3")
            yield Label("Provider API key")
            with Vertical(classes="key-row"):
                yield Select(
                    [("groq", "groq"), ("deepgram", "deepgram")],
                    id="key-provider-select",
                )
                yield Input(placeholder="Paste API key", password=True, id="key-input")
                yield Button("Save key", id="save-key-btn", variant="primary")

    def _hotkey_section(self) -> ComposeResult:
        with Vertical(id="hotkey", classes="settings-section"):
            yield from self._head("hotkey")
            yield Label("Hotkey mode")
            yield Select(
                [("both", "both"), ("ptt", "ptt"), ("toggle", "toggle")],
                id="hotkey-mode-select",
            )
            yield Label("Hotkey binding (e.g. ctrl+alt+space)")
            yield Input(id="hotkey-binding")
            yield Label("Cancel binding (e.g. esc)")
            yield Input(id="hotkey-cancel-binding")
            yield Label("PTT hold threshold (ms, 100–500)")
            yield Input(id="hotkey-ptt-hold-ms", value="200")
            yield Label("Toggle double-press window (ms, 200–1000)")
            yield Input(id="hotkey-toggle-ms", value="400")
            yield Label("Streaming mode")
            yield Select(
                [("auto", "auto"), ("on", "on"), ("off", "off")],
                id="hotkey-streaming-select",
            )
            yield Label("Minimum duration (ms)")
            yield Input(id="hotkey-min-duration-ms", value="250")
            yield Button("Save hotkey", id="save-hotkey-btn", variant="primary")

    def _audio_section(self) -> ComposeResult:
        with Vertical(id="audio", classes="settings-section"):
            yield from self._head("audio")
            yield Label("Input device (name or index; empty = default)")
            yield Input(id="audio-device", placeholder="default")
            yield Label("Sample rate (read-only)")
            yield Static("16000 Hz", id="audio-sample-rate")
            yield Checkbox("Save last recording (debug)", id="audio-save-recording")
            yield Button("Save audio", id="save-audio-btn", variant="primary")

    def _indicator_section(self) -> ComposeResult:
        with Vertical(id="indicator", classes="settings-section"):
            yield from self._head("indicator")
            yield Checkbox("Overlay indicator enabled", id="indicator-enabled")
            yield Label("Size (px)")
            yield Input(id="indicator-size", value="48")
            yield Label("Offset X (px)")
            yield Input(id="indicator-offset-x", value="16")
            yield Label("Offset Y (px)")
            yield Input(id="indicator-offset-y", value="16")
            yield Label("Sound cues folder")
            yield Static("", id="sounds-dir")
            yield Checkbox("Indicator sound cue", id="indicator-sound-enabled")
            yield Label("Volume (0-100)")
            yield Input(id="sound-volume", value="75")
            yield Label("Max cue length (seconds, 0.1–2.0)")
            yield Input(id="sound-max-seconds", value="0.5")
            yield Label("Start cue")
            with Horizontal(classes="sound-row"):
                yield Select(
                    [("Built-in chime", _BUILTIN_SOUND)],
                    id="sound-start-select",
                    classes="sound-select",
                )
                yield Button("Browse…", id="browse-start-sound", classes="sound-btn")
                yield Button("Built-in", id="clear-start-sound", classes="sound-btn")
            yield Label("Stop cue")
            with Horizontal(classes="sound-row"):
                yield Select(
                    [("Built-in chime", _BUILTIN_SOUND)],
                    id="sound-stop-select",
                    classes="sound-select",
                )
                yield Button("Browse…", id="browse-stop-sound", classes="sound-btn")
                yield Button("Built-in", id="clear-stop-sound", classes="sound-btn")
            yield Label("Import from path (paste a .wav path below)")
            yield Input(
                id="sound-import-path",
                placeholder=r"C:\path\to\cue.wav",
            )
            with Horizontal(classes="sound-row"):
                yield Select(
                    [("start", "Start cue"), ("stop", "Stop cue")],
                    id="sound-import-role",
                    classes="sound-select",
                )
                yield Button(
                    "Import path",
                    id="import-sound-path-btn",
                    classes="sound-btn",
                )
            yield Button("Save indicator", id="save-indicator-btn", variant="primary")

    def _injection_section(self) -> ComposeResult:
        with Vertical(id="injection", classes="settings-section"):
            yield from self._head("injection")
            yield Checkbox("Injection enabled", id="inject-enabled")
            yield Checkbox(
                "Restore clipboard after paste",
                id="inject-restore-clipboard",
            )

    def _text_section(self) -> ComposeResult:
        with Vertical(id="text", classes="settings-section"):
            yield from self._head("text")
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
            yield Checkbox("Vocabulary hints enabled", id="vocabulary-enabled")
            yield Static(
                "Manage terms via CLI: sybl config vocab add <term>",
                id="vocabulary-hint",
            )

    def _advanced_section(self) -> ComposeResult:
        with Vertical(id="advanced", classes="settings-section"):
            yield from self._head("advanced")
            yield Label("Log level")
            yield Select(
                [
                    ("DEBUG", "DEBUG"),
                    ("INFO", "INFO"),
                    ("WARNING", "WARNING"),
                    ("ERROR", "ERROR"),
                ],
                id="logging-level-select",
            )
            yield Label("History size (entries)")
            yield Input(id="ipc-history-size", value="100")
            yield Label("Log ring buffer size")
            yield Input(id="logging-ring-size", value="500")
            yield Button("Save advanced", id="save-advanced-btn", variant="primary")

    async def on_mount(self) -> None:
        nav = self.query_one("#settings-nav-list", ListView)
        nav.index = 0
        config = await self.app.ipc.get_config()
        provider = config.get("provider", {})
        if isinstance(provider, dict):
            self.query_one("#provider-select", Select).value = str(
                provider.get("preferred", "groq")
            )
            fallback = provider.get("fallback_order", [])
            if isinstance(fallback, list):
                self.query_one("#provider-fallback", Input).value = ", ".join(
                    str(item) for item in fallback
                )
            groq = provider.get("groq", {})
            if isinstance(groq, dict):
                self.query_one("#groq-model", Input).value = str(
                    groq.get("model", "whisper-large-v3-turbo")
                )
            deepgram = provider.get("deepgram", {})
            if isinstance(deepgram, dict):
                self.query_one("#deepgram-model", Input).value = str(
                    deepgram.get("model", "nova-3")
                )
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
            self.query_one("#hotkey-ptt-hold-ms", Input).value = str(
                hotkey.get("ptt_hold_ms", 200)
            )
            self.query_one("#hotkey-toggle-ms", Input).value = str(
                hotkey.get("toggle_double_press_ms", 400)
            )
            self.query_one("#hotkey-streaming-select", Select).value = str(
                hotkey.get("streaming", "auto")
            )
            self.query_one("#hotkey-min-duration-ms", Input).value = str(
                hotkey.get("min_duration_ms", 250)
            )
        audio = config.get("audio", {})
        if isinstance(audio, dict):
            device = audio.get("device")
            self.query_one("#audio-device", Input).value = (
                str(device) if device is not None else ""
            )
            rate = audio.get("sample_rate", 16000)
            self.query_one("#audio-sample-rate", Static).update(f"{rate} Hz")
            self.query_one("#audio-save-recording", Checkbox).value = bool(
                audio.get("save_last_recording", True)
            )
        indicator = config.get("indicator", {})
        if isinstance(indicator, dict):
            self.query_one("#indicator-enabled", Checkbox).value = bool(
                indicator.get("enabled", True)
            )
            self.query_one("#indicator-size", Input).value = str(
                indicator.get("size_px", 48)
            )
            self.query_one("#indicator-offset-x", Input).value = str(
                indicator.get("offset_x", 16)
            )
            self.query_one("#indicator-offset-y", Input).value = str(
                indicator.get("offset_y", 16)
            )
            self.query_one("#indicator-sound-enabled", Checkbox).value = bool(
                indicator.get("sound_enabled", False)
            )
            volume = float(indicator.get("sound_volume", 0.75))
            self.query_one("#sound-volume", Input).value = str(int(round(volume * 100)))
            self.query_one("#sound-max-seconds", Input).value = str(
                indicator.get("sound_max_seconds", 0.5)
            )
        inject = config.get("inject", {})
        if isinstance(inject, dict):
            self.query_one("#inject-enabled", Checkbox).value = bool(
                inject.get("enabled", True)
            )
            self.query_one("#inject-restore-clipboard", Checkbox).value = bool(
                inject.get("restore_clipboard", True)
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
        vocabulary = config.get("vocabulary", {})
        if isinstance(vocabulary, dict):
            self.query_one("#vocabulary-enabled", Checkbox).value = bool(
                vocabulary.get("enabled", True)
            )
        logging_cfg = config.get("logging", {})
        if isinstance(logging_cfg, dict):
            self.query_one("#logging-level-select", Select).value = str(
                logging_cfg.get("level", "INFO")
            )
            self.query_one("#logging-ring-size", Input).value = str(
                logging_cfg.get("ring_buffer_size", 500)
            )
        ipc_cfg = config.get("ipc", {})
        if isinstance(ipc_cfg, dict):
            self.query_one("#ipc-history-size", Input).value = str(
                ipc_cfg.get("history_size", 100)
            )
        await self._refresh_sound_controls()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "settings-nav-list":
            return
        index = event.list_view.index
        if index is None or index < 0 or index >= len(_SECTIONS):
            return
        section_key, _ = _SECTIONS[index]
        self.query_one("#settings-content", ContentSwitcher).current = section_key

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "save-key-btn":
            await self._save_key()
        elif button_id == "save-hotkey-btn":
            await self._save_hotkey()
        elif button_id == "save-audio-btn":
            await self._save_audio()
        elif button_id == "save-indicator-btn":
            await self._save_indicator_settings()
        elif button_id == "save-advanced-btn":
            await self._save_advanced()
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
        mode = str(self.query_one("#hotkey-mode-select", Select).value or "both")
        ptt_hold_raw = self.query_one("#hotkey-ptt-hold-ms", Input).value.strip()
        toggle_ms_raw = self.query_one("#hotkey-toggle-ms", Input).value.strip()
        min_duration_raw = self.query_one(
            "#hotkey-min-duration-ms",
            Input,
        ).value.strip()
        streaming = str(
            self.query_one("#hotkey-streaming-select", Select).value or "auto"
        )
        try:
            parse_binding(binding)
            parse_binding(cancel)
        except BindingParseError as exc:
            self._set_status(f"Invalid binding: {exc}")
            return
        try:
            ptt_hold_ms = int(ptt_hold_raw)
            toggle_ms = int(toggle_ms_raw)
            min_duration_ms = int(min_duration_raw)
        except ValueError:
            self._set_status("Numeric hotkey fields must be integers.")
            return
        if ptt_hold_ms < 100 or ptt_hold_ms > 500:
            self._set_status("PTT hold must be between 100 and 500 ms.")
            return
        if toggle_ms < 200 or toggle_ms > 1000:
            self._set_status("Toggle window must be between 200 and 1000 ms.")
            return
        if min_duration_ms < 0:
            self._set_status("Minimum duration must be non-negative.")
            return
        await self.app.ipc.patch_config(
            {
                "hotkey": {
                    "mode": mode,
                    "binding": binding,
                    "cancel_binding": cancel,
                    "ptt_hold_ms": ptt_hold_ms,
                    "toggle_double_press_ms": toggle_ms,
                    "streaming": streaming,
                    "min_duration_ms": min_duration_ms,
                }
            }
        )
        self._set_status("Hotkey settings saved.")
        await self.app.refresh_dashboard()

    async def _save_audio(self) -> None:
        device_raw = self.query_one("#audio-device", Input).value.strip()
        device = device_raw if device_raw else None
        await self.app.ipc.patch_config(
            {
                "audio": {
                    "device": device,
                    "save_last_recording": self.query_one(
                        "#audio-save-recording",
                        Checkbox,
                    ).value,
                }
            }
        )
        self._set_status("Audio settings saved.")
        await self.app.refresh_dashboard()

    async def _save_indicator_settings(self) -> None:
        volume_raw = self.query_one("#sound-volume", Input).value.strip()
        size_raw = self.query_one("#indicator-size", Input).value.strip()
        offset_x_raw = self.query_one("#indicator-offset-x", Input).value.strip()
        offset_y_raw = self.query_one("#indicator-offset-y", Input).value.strip()
        max_seconds_raw = self.query_one("#sound-max-seconds", Input).value.strip()
        try:
            volume_pct = int(volume_raw)
            size_px = int(size_raw)
            offset_x = int(offset_x_raw)
            offset_y = int(offset_y_raw)
            max_seconds = float(max_seconds_raw)
        except ValueError:
            self._set_status("Check indicator numeric fields.")
            return
        if volume_pct < 0 or volume_pct > 100:
            self._set_status("Volume must be between 0 and 100.")
            return
        if size_px < 16 or size_px > 256:
            self._set_status("Indicator size must be between 16 and 256 px.")
            return
        if max_seconds <= 0 or max_seconds > 2.0:
            self._set_status("Max cue length must be between 0.1 and 2.0 seconds.")
            return

        start_value = str(self.query_one("#sound-start-select", Select).value)
        stop_value = str(self.query_one("#sound-stop-select", Select).value)
        indicator_patch: dict = {
            "enabled": self.query_one("#indicator-enabled", Checkbox).value,
            "size_px": size_px,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "sound_enabled": self.query_one(
                "#indicator-sound-enabled",
                Checkbox,
            ).value,
            "sound_volume": volume_pct / 100.0,
            "sound_max_seconds": max_seconds,
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
        self._set_status("Indicator settings saved.")
        await self._refresh_sound_controls()
        await self.app.refresh_dashboard()

    async def _save_advanced(self) -> None:
        level = str(self.query_one("#logging-level-select", Select).value or "INFO")
        try:
            history_size = int(self.query_one("#ipc-history-size", Input).value.strip())
            ring_size = int(self.query_one("#logging-ring-size", Input).value.strip())
        except ValueError:
            self._set_status("History and ring buffer sizes must be integers.")
            return
        if history_size < 1 or ring_size < 1:
            self._set_status("Sizes must be at least 1.")
            return
        await self.app.ipc.patch_config(
            {
                "logging": {"level": level, "ring_buffer_size": ring_size},
                "ipc": {"history_size": history_size},
            }
        )
        self._set_status("Advanced settings saved.")

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
        checkbox_id = event.checkbox.id
        if checkbox_id == "inject-enabled":
            patch = {"inject": {"enabled": event.value}}
        elif checkbox_id == "inject-restore-clipboard":
            patch = {"inject": {"restore_clipboard": event.value}}
        elif checkbox_id == "postprocess-enabled":
            patch = {"postprocess": {"enabled": event.value}}
        elif checkbox_id == "trim-fillers":
            patch = {"postprocess": {"trim_fillers": event.value}}
        elif checkbox_id == "capitalize":
            patch = {"postprocess": {"capitalize": event.value}}
        elif checkbox_id == "ensure-punctuation":
            patch = {"postprocess": {"ensure_punctuation": event.value}}
        elif checkbox_id == "collapse-repeated":
            patch = {"postprocess": {"collapse_repeated_words": event.value}}
        elif checkbox_id == "normalize-quotes":
            patch = {"postprocess": {"normalize_quotes": event.value}}
        elif checkbox_id == "trim-punct-space":
            patch = {"postprocess": {"trim_space_before_punctuation": event.value}}
        elif checkbox_id == "voice-commands-enabled":
            patch = {"voice_commands": {"enabled": event.value}}
        elif checkbox_id == "vocabulary-enabled":
            patch = {"vocabulary": {"enabled": event.value}}
        elif checkbox_id == "indicator-enabled":
            patch = {"indicator": {"enabled": event.value}}
        elif checkbox_id == "indicator-sound-enabled":
            patch = {"indicator": {"sound_enabled": event.value}}
        elif checkbox_id == "audio-save-recording":
            patch = {"audio": {"save_last_recording": event.value}}
        else:
            return
        await self.app.ipc.patch_config(patch)
        self._set_status("Updated configuration.")
        await self.app.refresh_dashboard()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "provider-fallback":
            raw = event.value.strip()
            order = [part.strip() for part in raw.split(",") if part.strip()]
            await self.app.ipc.patch_config({"provider": {"fallback_order": order}})
            self._set_status("Fallback order saved.")
            await self.app.refresh_dashboard()
        elif event.input.id in ("groq-model", "deepgram-model"):
            if event.input.id == "groq-model":
                await self.app.ipc.patch_config(
                    {"provider": {"groq": {"model": event.value.strip()}}}
                )
            else:
                await self.app.ipc.patch_config(
                    {"provider": {"deepgram": {"model": event.value.strip()}}}
                )
            self._set_status("Provider model saved.")

    def _set_status(self, message: str) -> None:
        self.query_one("#settings-status", Static).update(message)

    def action_dismiss(self) -> None:
        self.dismiss(None)
