from data import BillingDataSource
from widgets.header import AppHeader

from textual import work
from textual.app import ComposeResult

from textual.screen import Screen
from textual.widgets import DataTable, Footer, Label

REFRESH_INTERVAL = 2.0

_EVENT_COLOR = {
    "input_tokens": "#58a6ff",
    "cached_input_tokens": "#3fb950",
    "reasoning_tokens": "#d29922",
    "output_tokens": "#e3b341",
    "api_call": "#bc8cff",
}


class UsageLogScreen(Screen):
    def __init__(self, data_source: BillingDataSource, **kwargs) -> None:
        super().__init__(**kwargs)

        self._data = data_source
        self._known_ids: set[str] = set()

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Label("Live usage events  (newest first)", classes="panel-title", id="log-title")

        yield DataTable(id="log-table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#log-table", DataTable)
        table.add_columns("Time", "Tenant", "Event type", "Quantity")

        self.set_interval(REFRESH_INTERVAL, self._refresh)
        self._refresh()

    @work(exclusive=True, group="log-refresh")
    async def _refresh(self) -> None:
        try:
            events = await self._data.recent_events(limit=60)
        except Exception:
            return

        self.query_one(AppHeader).mode = self._data.mode
        new_events = [e for e in events if e.id not in self._known_ids]

        if not new_events:
            return

        table = self.query_one("#log-table", DataTable)

        for e in sorted(new_events, key=lambda ev: ev.created_at):
            self._known_ids.add(e.id)

            table.add_row(
                e.created_at.strftime("%H:%M:%S"),
                e.tenant_id,

                f"[{_EVENT_COLOR.get(e.event_type, '#d8dee9')}]{e.event_type}[/]",
                f"{e.quantity:,}",

                key=e.id,
            )

        while table.row_count > 200:
            oldest_key = next(iter(table.rows))
            table.remove_row(oldest_key)

        table.scroll_end(animate=False)
