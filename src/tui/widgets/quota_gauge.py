from rich.text import Text

from textual.reactive import reactive
from textual.widgets import Static

from billing.tui.data import TenantUsage

_BAR_WIDTH = 32

_BLOCK_FULL = "█"
_BLOCK_EMPTY = "░"


def _threshold_color(pct: float) -> str:
    if pct >= 1.0:
        return "#f85149"
    if pct >= 0.8:
        return "#d29922"

    return "#3fb950"


def _render_bar(pct: float) -> Text:
    filled = min(_BAR_WIDTH, round(_BAR_WIDTH * min(pct, 1.0)))
    color = _threshold_color(pct)

    bar = Text()
 
    bar.append(_BLOCK_FULL * filled, style=color)
    bar.append(_BLOCK_EMPTY * (_BAR_WIDTH - filled), style="#2a2f3a")
 
    if pct > 1.0:
        bar.append("  OVERAGE", style="bold #f85149")
 
    return bar


class QuotaGauge(Static, can_focus=True):
    tenant: reactive[TenantUsage | None] = reactive(None, layout=True)

    def __init__(self, tenant: TenantUsage, **kwargs) -> None:
        super().__init__(**kwargs)

        self.tenant = tenant

    def render(self) -> Text:
        t = self.tenant

        if t is None:
            return Text("")

        status_style = "status-active" if t.status == "active" else "status-past_due"

        header = Text()

        header.append(f"{t.tenant_name:<22}", style="bold #d8dee9")
        header.append(f" {t.plan_name.upper():<8}", style="#58a6ff")

        header.append(f" {t.status.upper()}", style="bold #f85149" if t.status != "active" else "#3fb950")
        header.append(f"   ${t.cost_cents / 100:,.2f}", style="bold #e3b341")

        bar = _render_bar(t.pct)

        numbers = Text(
            f"{t.used:,} / {t.limit:,}  ({t.pct * 100:.1f}%)",
            style="#7f8ea3",
        )

        out = Text()

        out.append(header)
        out.append("\n")

        out.append(bar)
        out.append("\n")

        out.append(numbers)

        return out

    def watch_tenant(self, _old, _new) -> None:
        self.refresh()
