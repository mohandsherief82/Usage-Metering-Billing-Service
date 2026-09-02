from data import BillingDataSource, TenantUsage
from widgets.header import AppHeader

from textual import work
from textual.app import ComposeResult

from textual.containers import Horizontal, Vertical
from textual.screen import Screen

from textual.widgets import Footer, Label, ListItem, ListView, Sparkline, Static

REFRESH_INTERVAL = 4.0


class TenantRow(ListItem):
    def __init__(self, tenant: TenantUsage) -> None:
        super().__init__(Label(self._label(tenant)), id=f"row-{tenant.tenant_id}")

        self.tenant_id = tenant.tenant_id

    @staticmethod
    def _label(t: TenantUsage) -> str:
        marker = "●" if t.status == "active" else "✕"

        return f"{marker} {t.tenant_name}  ({t.plan_name})"


class TenantsScreen(Screen):
    def __init__(self, data_source: BillingDataSource, **kwargs) -> None:
        super().__init__(**kwargs)

        self._data = data_source
        self._tenants: dict[str, TenantUsage] = {}

        self._selected: str | None = None

    def compose(self) -> ComposeResult:
        yield AppHeader()

        with Horizontal():
            yield ListView(id="tenants-list")

            with Vertical(id="tenant-detail", classes="panel"):
                yield Static("Select a tenant to see details", id="detail-body")

        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._refresh)

        self._refresh()

    @work(exclusive=True, group="tenants-refresh")
    async def _refresh(self) -> None:
        try:
            tenants = await self._data.list_tenants_usage()
        except Exception:
            return

        self.query_one(AppHeader).mode = self._data.mode
        self._tenants = {t.tenant_id: t for t in tenants}

        self._sync_list()

        if self._selected and self._selected in self._tenants:
            self._render_detail(self._tenants[self._selected])

    def _sync_list(self) -> None:
        list_view = self.query_one("#tenants-list", ListView)
        existing_ids = {item.tenant_id for item in list_view.children if isinstance(item, TenantRow)}

        current_ids = set(self._tenants)

        for tid in current_ids - existing_ids:
            list_view.append(TenantRow(self._tenants[tid]))

        for item in list(list_view.children):
            if isinstance(item, TenantRow) and item.tenant_id not in current_ids:
                item.remove()

        if self._selected is None and self._tenants:
            first_id = next(iter(self._tenants))

            self._selected = first_id
            self._render_detail(self._tenants[first_id])

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item

        if isinstance(item, TenantRow):
            self._selected = item.tenant_id
            self._render_detail(self._tenants[item.tenant_id])

    def _render_detail(self, t: TenantUsage) -> None:
        body = self.query_one("#detail-body", Static)

        status_html = (
            "[b green]ACTIVE[/b green]" if t.status == "active" else f"[b red]{t.status.upper()}[/b red]"
        )

        lines = [
            f"[b]{t.tenant_name}[/b]  ({t.tenant_id})",
            "",
            f"[dim]Plan[/dim]        [b cyan]{t.plan_name.upper()}[/b cyan]",
            f"[dim]Status[/dim]      {status_html}",
            f"[dim]Usage[/dim]       {t.used:,} / {t.limit:,}  ({t.pct * 100:.1f}%)",
            f"[dim]Cost (MTD)[/dim]  [b #e3b341]${t.cost_cents / 100:,.2f}[/b #e3b341]",
        ]

        body.update("\n".join(lines))

        detail = self.query_one("#tenant-detail", Vertical)

        for old in detail.query("Sparkline"):
            old.remove()

        for old in detail.query(".trend-label"):
            old.remove()

        if t.history:
            detail.mount(Label("Usage trend", classes="field-label trend-label"))

            detail.mount(Sparkline(t.history, summary_function=max))
