from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Request, status

from sqlalchemy.orm import Session

from db.models import WebhookEvent
from db.session import get_db

from services.stripe_service import StripeService

webhook_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@webhook_router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    payload = await request.body()

    event = StripeService.verify_webhook_signature(payload, stripe_signature)

    existing_event = db.query(WebhookEvent).filter_by(id=event.id).first()

    if existing_event:
        return {"status": "ignored", "reason": "duplicate event"}

    webhook_record = WebhookEvent(
        id=event.id,
        type=event.type,
        processed_at=datetime.now(timezone.utc),
    )

    db.add(webhook_record)
    db.commit()

    return {"status": "success", "event_id": event.id}
