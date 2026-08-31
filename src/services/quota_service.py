from fastapi import HTTPException, status

from sqlalchemy.orm import Session

from src.db.models import Tenant, Plan, UsageEvent, TenantStatus


class QuotaService:

    def __init__(self, db: Session):
        self.db = db

    def check_quota(self, tenant_id: str) -> None:
        tenant = self.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"Tenant '{tenant_id}' not found."},
            )

        status_val = tenant.status.value if isinstance(tenant.status, TenantStatus) else tenant.status

        if tenant.status in ["past_due", "canceled"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "message": f"Tenant '{tenant_id}' account status is '{status_val}'. Payment required."
                },
            )

        plan = self.db.query(Plan).filter_by(id=tenant.plan_id).first()

        if not plan:
            return

        total_used = (
            self.db.query(UsageEvent).filter_by(tenant_id=tenant_id).count()
        )

        if total_used > plan.monthly_api_call_quota:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": f"tenant {tenant_id} is at {total_used}/{plan.monthly_api_call_quota} API calls for this billing period"
                },
            )
