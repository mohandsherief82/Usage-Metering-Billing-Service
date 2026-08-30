import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, TenantStatus, Tenant


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    acme_tenant = Tenant(id="acme", name="Acme Corp", status=TenantStatus.ACTIVE)

    session.add(acme_tenant)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(engine)