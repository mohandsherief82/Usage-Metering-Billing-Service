import stripe

from fastapi import HTTPException, status

from src.config import settings


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
