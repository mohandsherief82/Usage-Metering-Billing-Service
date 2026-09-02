import calendar
from datetime import datetime, timezone

from fastapi import HTTPException, status

from sqlalchemy.orm import Session

from src.db.models import Plan, Subscription, SubscriptionStatus, Tenant, TenantStatus, UsageEvent


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
            retry_after_seconds = self._seconds_until_quota_reset(tenant_id)

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": f"tenant {tenant_id} is at {total_used}/{plan.monthly_api_call_quota} API calls for this billing period"
                },
                headers={"Retry-After": str(retry_after_seconds)},
            )

    def _seconds_until_quota_reset(self, tenant_id: str) -> int:
        subscription = (
            self.db.query(Subscription)
            .filter_by(tenant_id=tenant_id, status=SubscriptionStatus.ACTIVE)
            .order_by(Subscription.current_period_end.desc())
            .first()
        )

        now = datetime.now(timezone.utc)

        if subscription:
            period_end = subscription.current_period_end

            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)

            if period_end > now:
                return max(1, int((period_end - now).total_seconds()))

        reset_at = self._end_of_current_calendar_month(now)

        return max(1, int((reset_at - now).total_seconds()))

    def _end_of_current_calendar_month(self, now: datetime) -> datetime:
        last_day = calendar.monthrange(now.year, now.month)[1]

        return now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=0)
