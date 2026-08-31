from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config import (PRICE_PER_API_CALL_CENTS,
    PRICE_INPUT_TOKEN_MICROCENTS,
    PRICE_CACHED_INPUT_TOKEN_MICROCENTS,
    PRICE_REASONING_TOKEN_MICROCENTS,
    PRICE_OUTPUT_TOKEN_MICROCENTS,
    MICROCENTS_PER_CENT
)

from src.db.models import UsageEvent, UsageEventType


class CostService:

    Event_UNIT_PRICES_MICROCENTS = {
        UsageEventType.API_CALL.value: PRICE_PER_API_CALL_CENTS * MICROCENTS_PER_CENT,
        UsageEventType.INPUT_TOKENS.value: PRICE_INPUT_TOKEN_MICROCENTS,
        UsageEventType.CACHED_INPUT_TOKENS.value: PRICE_CACHED_INPUT_TOKEN_MICROCENTS,
        UsageEventType.REASONING_TOKENS.value: PRICE_REASONING_TOKEN_MICROCENTS,
        UsageEventType.OUTPUT_TOKENS.value: PRICE_OUTPUT_TOKEN_MICROCENTS
    }

    def __init__(self, db: Session):
        self.db = db

    def rollup(
            self, tenant_id: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        results = (
            self.db.query(UsageEvent.event_type, func.sum(UsageEvent.quantity))
            .filter(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.created_at >= start_time,
                UsageEvent.created_at < end_time
            )
            .group_by(UsageEvent.event_type)
            .all()
        )

        breakdown: List[Dict[str, Any]] = []

        total_microcents = 0

        for event_type_enum, total_quantity in results:
            event_type = event_type_enum.value if hasattr(event_type_enum, "value") else str(event_type_enum)

            quantity = int(total_quantity or 0)
            unit_price = self.Event_UNIT_PRICES_MICROCENTS.get(event_type, 0)

            cost_microcents = quantity * unit_price

            total_microcents = (total_microcents + MICROCENTS_PER_CENT - 1) // MICROCENTS_PER_CENT if total_microcents > 0 else 0

            breakdown.append(
                {
                    "event_type": event_type,
                    "quantity": quantity,
                    "unit_price_microcents": unit_price,
                    "total_microcents": cost_microcents,
                }
            )

        total_cents = (total_microcents + MICROCENTS_PER_CENT - 1) // MICROCENTS_PER_CENT if total_microcents > 0 else 0

        return {
            "tenant_id": tenant_id,
            "start_time": start_time,
            "end_time": end_time,
            "total_microcents": total_microcents,
            "total_cents": total_cents,
            "breakdown": breakdown,
        }
