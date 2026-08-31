from typing import Any, Optional, Dict
from pydantic import BaseModel, Field


class UsageRecordRequest(BaseModel):

    tenant_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    idempotency_key: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None

class CheckoutRequest(BaseModel):
    tenant_id: str
    plan_id: int
    success_url: str = "http://localhost:8000/success"
    cancel_url: str = "http://localhost:8000/cancel"
