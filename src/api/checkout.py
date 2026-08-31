from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from src.db.models import Plan, Tenant
from src.db.session import get_db

from src.services.stripe_service import StripeService
from src.schemas import CheckoutRequest

checkout_router = APIRouter()


@checkout_router.post("/checkout", status_code=status.HTTP_200_OK)
def create_checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter_by(id=payload.tenant_id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Tenant '{payload.tenant_id}' not found."},
        )

    plan = db.query(Plan).filter_by(id=payload.plan_id).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Plan ID {payload.plan_id} not found."},
        )

    if not plan.stripe_price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Plan '{plan.name}' does not have a valid stripe_price_id configured."},
        )

    session = StripeService.create_checkout_session(
        tenant_id=tenant.id,
        stripe_price_id=plan.stripe_price_id,

        success_url=payload.success_url,
        cancel_url=payload.cancel_url,

        stripe_customer_id=tenant.stripe_customer_id,
    )

    return {
        "checkout_url": session.url,
        "session_id": session.id,
    }
