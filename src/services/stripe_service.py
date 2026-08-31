import stripe
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from src.config import settings
from src.db.models import Plan, Subscription, SubscriptionStatus, Tenant, TenantStatus


class StripeService:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    @staticmethod
    def verify_webhook_signature(payload: bytes, sig_header: str) -> stripe.Event:
        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe-Signature header",
            )

        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )

            return event
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid webhook signature: {str(e)}",
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid webhook payload: {str(e)}",
            )

    @staticmethod
    def create_checkout_session(
            tenant_id: str,
            stripe_price_id: str,
            success_url: str,
            cancel_url: str,
            stripe_customer_id: str | None = None,
    ) -> stripe.checkout.Session:
        try:
            session_kwargs = {
                "mode": "subscription",
                "payment_method_types": ["card"],

                "line_items": [
                    {
                        "price": stripe_price_id,
                        "quantity": 1,
                    }
                ],

                "client_reference_id": tenant_id,
                "metadata": {"tenant_id": tenant_id},

                "success_url": success_url,
                "cancel_url": cancel_url,
            }

            if stripe_customer_id:
                session_kwargs["customer"] = stripe_customer_id

            return stripe.checkout.Session.create(**session_kwargs)

        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe Checkout error: {str(e)}",
            )

    @staticmethod
    def handle_checkout_session_completed(event_data: dict, db: Session) -> None:
        session_obj = event_data.get("object", {})
        tenant_id = session_obj.get("client_reference_id") or session_obj.get("metadata", {}).get("tenant_id")

        stripe_customer_id = session_obj.get("customer")
        stripe_subscription_id = session_obj.get("subscription")

        if not tenant_id:
            return

        tenant = db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant:
            return

        if stripe_customer_id:
            tenant.stripe_customer_id = stripe_customer_id

        if stripe_subscription_id:
            stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
            price_id = stripe_sub["items"]["data"][0]["price"]["id"]

            plan = db.query(Plan).filter_by(stripe_price_id=price_id).first()

            if plan:
                tenant.plan_id = plan.id

                tenant.status = TenantStatus.ACTIVE

            sub_record = db.query(Subscription).filter_by(stripe_subscription_id=stripe_subscription_id).first()

            period_start = datetime.fromtimestamp(stripe_sub["current_period_start"], tz=timezone.utc)
            period_end = datetime.fromtimestamp(stripe_sub["current_period_end"], tz=timezone.utc)

            if not sub_record:
                sub_record = Subscription(
                    tenant_id=tenant.id,
                    plan_id=plan.id if plan else tenant.plan_id,

                    stripe_subscription_id=stripe_subscription_id,
                    status=SubscriptionStatus(stripe_sub["status"]),

                    current_period_start=period_start,
                    current_period_end=period_end,
                )

                db.add(sub_record)
            else:
                sub_record.status = SubscriptionStatus(stripe_sub["status"])
                sub_record.current_period_start = period_start

                sub_record.current_period_end = period_end

        db.commit()

    @staticmethod
    def handle_subscription_updated(event_data: dict, db: Session) -> None:
        sub_obj = event_data.get("object", {})
        stripe_subscription_id = sub_obj.get("id")

        stripe_status = sub_obj.get("status")

        sub_record = db.query(Subscription).filter_by(stripe_subscription_id=stripe_subscription_id).first()

        if not sub_record:
            return

        sub_record.status = SubscriptionStatus(stripe_status)
        sub_record.current_period_start = datetime.fromtimestamp(sub_obj["current_period_start"], tz=timezone.utc)

        sub_record.current_period_end = datetime.fromtimestamp(sub_obj["current_period_end"], tz=timezone.utc)

        tenant = db.query(Tenant).filter_by(id=sub_record.tenant_id).first()

        if tenant:
            if stripe_status == "past_due":
                tenant.status = TenantStatus.PAST_DUE
            elif stripe_status == "active":
                tenant.status = TenantStatus.ACTIVE

        db.commit()

    @staticmethod
    def handle_subscription_deleted(event_data: dict, db: Session) -> None:
        sub_obj = event_data.get("object", {})
        stripe_subscription_id = sub_obj.get("id")

        sub_record = db.query(Subscription).filter_by(stripe_subscription_id=stripe_subscription_id).first()

        if sub_record:
            sub_record.status = SubscriptionStatus.CANCELED

            tenant = db.query(Tenant).filter_by(id=sub_record.tenant_id).first()

            if tenant:
                tenant.status = TenantStatus.CANCELED

            db.commit()
