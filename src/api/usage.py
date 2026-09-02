from fastapi import APIRouter, Depends, Header, status

from sqlalchemy.orm import Session

from src.db.session import get_db

from src.schemas import UsageRecordRequest, UsageRecordResponse
from src.services.meter_service import MeterService
from src.services.quota_service import QuotaService


usage_router = APIRouter()

@usage_router.post("/usage/record", response_model=UsageRecordResponse)
def record_usage(
    payload: UsageRecordRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    payload.idempotency_key = idempotency_key

    meter_service = MeterService(db)

    event, is_created = meter_service.record(
        tenant_id=payload.tenant_id,
        event_type=payload.event_type,

        quantity=payload.quantity,
        idempotency_key=payload.idempotency_key,

        metadata=payload.metadata,
    )

    if is_created:
        quota_service = QuotaService(db)

        quota_service.check_quota(payload.tenant_id)

    return UsageRecordResponse(
        id=event.id,
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        quantity=event.quantity,
        metadata=event.meta,
        idempotency_key=event.idempotency_key,
        created_at=event.created_at,
    )