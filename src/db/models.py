import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Index, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    slug: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    name: Mapped[str] = mapped_column(String(64), nullable=False)

    monthly_api_call_quota: Mapped[int] = mapped_column(Integer, nullable=False)

    monthly_ai_token_quota: Mapped[int] = mapped_column(Integer, nullable=False)

    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenants: Mapped[list["Tenant"]] = relationship(back_populates="plan")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")

    def __repr__(self) -> str:  # pragma: no cover — debugging aid only
        return (
            f"Plan(id={self.id}, slug={self.slug!r}, "
            f"api_calls={self.monthly_api_call_quota}, "
            f"ai_tokens={self.monthly_ai_token_quota})"
        )


class SubscriptionStatus(str, enum.Enum):

    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"


class Subscription(Base):

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)

    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )

    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, length=20),
        nullable=False,
    )

    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")

    def __repr__(self) -> str:
        return (
            f"Subscription(id={self.id}, tenant_id={self.tenant_id!r}, "
            f"stripe_subscription_id={self.stripe_subscription_id!r}, "
            f"status={self.status.value})"
        )


class UsageEventType(str, enum.Enum):

    API_CALL = "api_call"
    INPUT_TOKENS = "input_tokens"
    CACHED_INPUT_TOKENS = "cached_input_tokens"
    REASONING_TOKENS = "reasoning_tokens"
    OUTPUT_TOKENS = "output_tokens"


class UsageEvent(Base):

    __tablename__ = "usage_events"
    __table_args__ = (
        Index("ix_usage_events_tenant_type_created", "tenant_id", "event_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)

    event_type: Mapped[UsageEventType] = mapped_column(
        Enum(UsageEventType, native_enum=False, length=32),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="usage_events")

    def __repr__(self) -> str:  # pragma: no cover — debugging aid only
        return (
            f"UsageEvent(id={self.id}, tenant_id={self.tenant_id!r}, "
            f"type={self.event_type.value}, qty={self.quantity}, "
            f"idempotency_key={self.idempotency_key!r})"
        )


class WebhookEvent(Base):

    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)

    type: Mapped[str] = mapped_column(String(255), nullable=False)

    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id"), nullable=True)

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"WebhookEvent(id={self.id!r}, type={self.type!r}, tenant_id={self.tenant_id!r})"
