from typing import Any, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from src.db.models import UsageEventType


class UsageRecordRequest(BaseModel):

    tenant_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    idempotency_key: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class UsageRecordResponse(BaseModel):
    id: int
    tenant_id: str
    event_type: UsageEventType
    quantity: int
    metadata: Optional[Dict[str, Any]] = None
    idempotency_key: str
    created_at: datetime

    # Constructed explicitly in api/usage.py rather than via from_attributes
    # auto-mapping — the ORM attribute is `meta` (not `metadata`, which
    # SQLAlchemy's DeclarativeBase reserves for its own schema registry),
    # so automatic attribute-name/alias lookup would silently pick up that
    # registry object instead of the real value. See meter_service.py for
    # the same underlying collision on the write side.
    model_config = ConfigDict(from_attributes=True)


class CheckoutRequest(BaseModel):
    tenant_id: str
    plan_id: int
    success_url: str = "http://localhost:8000/success"
    cancel_url: str = "http://localhost:8000/cancel"
