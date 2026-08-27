"""
QuotaService — compares a tenant's rolled-up usage for the current billing
period against their Plan.monthly_quota.

Returns an explicit allow/deny + status code + human-readable message; see
GUIDE.md §4 for the 402-vs-429 convention you choose and must document.
"""

# TODO: implement check_quota()
