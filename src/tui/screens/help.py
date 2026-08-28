from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static

_ROWS = [
    ("d", "Dashboard — fleet quota gauges"),
    ("t", "Tenants — browse tenants, view trend detail"),
    ("l", "Usage log — live event tail"),
    ("r", "Refresh now (dashboard)"),
    ("?", "Toggle this help"),
    ("q", "Quit"),
    ("↑ / ↓ / tab", "Navigate lists / focus"),
]


class HelpScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close"), ("question_mark", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Label("Keybindings", classes="title")

            for key, desc in _ROWS:
                yield Static(f"[b #58a6ff]{key:<10}[/b #58a6ff] {desc}")

            yield Label("")
            yield Label("[dim]press escape or ? to close[/dim]")

    def action_dismiss(self, result=None) -> None:
        self.dismiss()
