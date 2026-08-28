from tui.data import BillingDataSource, TenantUsage
from tui.widgets import AppHeader, QuotaGauge, StatCard
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Label

REFRESH_INTERVAL = 3.0


class DashboardScreen(Screen):
    BINDINGS = [
        ("r", "refresh_now", "Refresh"),
    ]

    def __init__(self, data_source: BillingDataSource, **kwargs) -> None:
        super().__init__(**kwargs)

        self._data = data_source
        self._gauges: dict[str, QuotaGauge] = {}

    def compose(self) -> ComposeResult:
        yield AppHeader()

        with Horizontal(id="stat-strip"):
            yield StatCard("TENANTS", accent="cyan", id="stat-tenants")
            yield StatCard("TOTAL COST (MTD)", accent="amber", id="stat-cost")

            yield StatCard("NEAR LIMIT (≥80%)", accent="green", id="stat-warn")
            yield StatCard("OVER LIMIT", accent="red", id="stat-over")

        yield Label("Fleet usage", classes="panel-title", id="fleet-title")
        yield VerticalScroll(id="gauge-list")

        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._refresh)

        self._refresh()

    def action_refresh_now(self) -> None:
        self._refresh()

    @work(exclusive=True, group="dashboard-refresh")
    async def _refresh(self) -> None:
        try:
            tenants = await self._data.list_tenants_usage()
        except Exception:
            return

        self._update_header_badge()

        self._update_stats(tenants)
        self._update_gauges(tenants)

    def _update_header_badge(self) -> None:
        try:
            self.query_one(AppHeader).mode = self._data.mode
        except Exception:
            pass

    def _update_stats(self, tenants: list[TenantUsage]) -> None:
        total_cost = sum(t.cost_cents for t in tenants) / 100
        near_limit = sum(1 for t in tenants if 0.8 <= t.pct < 1.0)

        over_limit = sum(1 for t in tenants if t.pct >= 1.0)

        self.query_one("#stat-tenants", StatCard).update_value(str(len(tenants)))
        self.query_one("#stat-cost", StatCard).update_value(f"${total_cost:,.2f}")

        self.query_one("#stat-warn", StatCard).update_value(str(near_limit))
        self.query_one("#stat-over", StatCard).update_value(str(over_limit))

    def _update_gauges(self, tenants: list[TenantUsage]) -> None:
        list_view = self.query_one("#gauge-list", VerticalScroll)
        seen = set()

        for t in sorted(tenants, key=lambda x: x.pct, reverse=True):
            seen.add(t.tenant_id)
            existing = self._gauges.get(t.tenant_id)

            if existing is None:
                gauge = QuotaGauge(t, id=f"gauge-{t.tenant_id}")

                self._gauges[t.tenant_id] = gauge

                list_view.mount(gauge)
            else:
                existing.tenant = t

        for tid in list(self._gauges):
            if tid not in seen:
                self._gauges.pop(tid).remove()
