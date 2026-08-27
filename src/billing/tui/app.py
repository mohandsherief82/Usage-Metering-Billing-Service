"""
Textual App entrypoint for the operator dashboard.

Screens (see GUIDE.md §7):
- Dashboard: live per-tenant used/limit/cost table, polling GET /usage
- Tenants: browse/select tenant
- UsageLog: tail of recent UsageEvents

Run with: uv run textual run --dev src/billing/tui/app.py
"""

# TODO: from textual.app import App; wire up screens/dashboard.py etc.


def run() -> None:
    raise NotImplementedError("wire up the Textual App and call .run()")
