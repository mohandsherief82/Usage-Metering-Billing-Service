from pathlib import Path

from textual.app import App

from tui.data import BillingDataSource
from tui.screens import DashboardScreen, HelpScreen, TenantsScreen, UsageLogScreen

THEME_PATH = Path(__file__).parent / "theme.tcss"


class LedgerApp(App):
    """A unique-themed, non-blocking terminal dashboard for usage & billing."""

    CSS_PATH = THEME_PATH
    TITLE = "LEDGER"

    BINDINGS = [
        ("d", "goto_dashboard", "Dashboard"),
        ("t", "goto_tenants", "Tenants"),
        ("l", "goto_log", "Usage log"),
        ("?", "show_help", "Help"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        
        self.data_source = BillingDataSource()

    def on_mount(self) -> None:
        self.install_screen(DashboardScreen(self.data_source), name="dashboard")
        self.install_screen(TenantsScreen(self.data_source), name="tenants")
        
        self.install_screen(UsageLogScreen(self.data_source), name="log")
        self.push_screen("dashboard")

    def action_goto_dashboard(self) -> None:
        self.switch_screen("dashboard")

    def action_goto_tenants(self) -> None:
        self.switch_screen("tenants")

    def action_goto_log(self) -> None:
        self.switch_screen("log")

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())


def run() -> None:
    LedgerApp().run()


if __name__ == "__main__":
    run()
