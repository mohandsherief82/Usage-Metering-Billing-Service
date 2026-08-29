from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from db.models import UsageEvent


class MeterService:

    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        tenant_id: str,
        event_type: str,
        quantity: int,
        idempotency_key: str,
        metadata: dict | None = None,
    ) -> tuple[UsageEvent, bool]:
        event = UsageEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            quantity=quantity,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )

        try:
            self.db.add(event)
            self.db.commit()

            self.db.refresh(event)

            return event, True
        except IntegrityError:
            self.db.rollback()
            existing_event = (
                self.db.query(UsageEvent)
                .filter_by(idempotency_key=idempotency_key)
                .first()
            )

            return existing_event, False
