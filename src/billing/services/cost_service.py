"""
CostService.rollup(tenant_id, period) -> { used, limit, cost }

Sums UsageEvent quantities by event_type for the period and multiplies by
the pinned per-unit constants in billing.config. AI token event types
(input_tokens, cached_input_tokens, reasoning_tokens, output_tokens) are
priced independently — never blended into a single average rate.
"""

# TODO: implement rollup()
