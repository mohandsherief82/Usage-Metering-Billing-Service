"""
MeterService.record(tenant_id, event_type, quantity, idempotency_key)

Contract (see GUIDE.md §3):
1. Attempt to insert a UsageEvent with this idempotency_key.
2. If a row with that key already exists, return the ORIGINAL result —
   do not insert a second event, do not re-run quota logic as if it were new.
3. Only a genuinely new event proceeds to quota checking.

This is the one place double-counting can be introduced or prevented —
keep it small and covered by tests/test_metering_idempotency.py.
"""

# TODO: implement record()
