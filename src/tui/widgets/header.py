from datetime import datetime

from data import SourceMode
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Label, Static


class AppHeader(Static):
    mode: reactive[SourceMode] = reactive(SourceMode.CONNECTING)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("LEDGER — Usage Metering & Billing", id="title")
            yield Label("", id="spacer")

            yield Label(datetime.now().strftime("%H:%M:%S"), id="clock")
            yield Label("○ CONNECTING", id="conn-connecting")

    def on_mount(self) -> None:
        self.set_interval(1.0, self._tick_clock)

    def _tick_clock(self) -> None:
        try:
            self.query_one("#clock", Label).update(datetime.now().strftime("%H:%M:%S"))
        except Exception:
            pass

    def watch_mode(self, _old: SourceMode, new: SourceMode) -> None:
        for badge_id in ("conn-live", "conn-demo", "conn-connecting"):
            try:
                self.query_one(f"#{badge_id}", Label).remove()
            except Exception:
                pass

        label_map = {
            SourceMode.LIVE: ("conn-live", "● LIVE"),
            SourceMode.DEMO: ("conn-demo", "◐ DEMO DATA"),

            SourceMode.CONNECTING: ("conn-connecting", "○ CONNECTING"),
        }

        badge_id, text = label_map[new]

        self.mount(Label(text, id=badge_id))
