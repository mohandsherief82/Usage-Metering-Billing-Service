from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical

from textual.reactive import reactive
from textual.widgets import Label, Static


class StatCard(Static):
    """A single 'VALUE / label' card, e.g. 47 tenants, $1,204.55 total cost."""

    value: reactive[str] = reactive("—")
    label: reactive[str] = reactive("")

    def __init__(self, label: str, value: str = "—", accent: str = "amber", **kwargs) -> None:
        super().__init__(**kwargs)
        self.label = label

        self.value = value
        self.add_class(f"accent-{accent}")

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.value, id="value", classes="value"),

            Label(self.label, id="label", classes="label"),
        )

    def update_value(self, value: str) -> None:
        self.value = value

        try:
            self.query_one("#value", Label).update(value)
        except Exception:
            pass
