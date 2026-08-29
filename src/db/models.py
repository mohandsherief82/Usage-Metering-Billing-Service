import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )

    plan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, native_enum=False, length=20),
        nullable=False,
        default=TenantStatus.ACTIVE,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"Tenant(id={self.id!r}, name={self.name!r}, "
            f"plan_id={self.plan_id}, status={self.status.value})"
        )


# class Plan(Base): ...
#     Once this lands, add:
#       Tenant.plan_id -> ForeignKey("plans.id")
# class Subscription(Base): ...
# class UsageEvent(Base): ...
#     idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
# class WebhookEvent(Base): ...
#     id: Mapped[str] = mapped_column(String(255), primary_key=True)  # = Stripe event id
