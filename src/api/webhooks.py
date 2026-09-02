from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Request, status

from sqlalchemy.orm import Session

from src.db.models import WebhookEvent
from src.db.session import get_db

from src.services.stripe_service import StripeService

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

    # event is a stripe.Event / StripeObject, not a dict — it does not
    # support .get(). Converting once here means every existing .get()
    # call inside the StripeService handlers (on session_obj / sub_obj)
    # keeps working unchanged, since to_dict() recursively converts every
    # nested StripeObject to a plain dict too.
    event_data = event.to_dict().get("data", {})

    if event.type == "checkout.session.completed":
        StripeService.handle_checkout_session_completed(event_data, db)
    elif event.type == "customer.subscription.updated":
        StripeService.handle_subscription_updated(event_data, db)
    elif event.type == "customer.subscription.deleted":
        StripeService.handle_subscription_deleted(event_data, db)

    return {"status": "success", "event_id": event.id}
