"""Static keyboard hint footer."""

from __future__ import annotations

from textual.widgets import Static


class KeyFooter(Static):
    """Dashboard keybinding hints."""

    DEFAULT_TEXT = (
        "[key-hint]s[/] settings  ·  "
        "[key-hint]e[/] edit config  ·  "
        "[key-hint]?[/] help  ·  "
        "[key-hint]/[/] filter  ·  "
        "[key-hint]y[/] copy  ·  "
        "[key-hint]↑↓[/] select  ·  "
        "[key-hint]q[/] quit"
    )

    def on_mount(self) -> None:
        self.update(self.DEFAULT_TEXT)
