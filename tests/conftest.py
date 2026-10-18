import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from main import app

# In-memory SQLite database specifically for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    # Seed baseline authentic data into test db
    db = TestingSessionLocal()
    try:
        from app.models import User
        # Run seed logic against test session
        from app.core.security import get_password_hash
        admin = User(
            username="test_admin",
            email="admin@test.local",
            hashed_password=get_password_hash("AdminPass123!"),
            full_name="Test Administrator",
            role="admin",
            is_active=True,
        )
        resident = User(
            username="test_resident",
            email="resident@test.local",
            hashed_password=get_password_hash("ResidentPass123!"),
            full_name="Test Citizen",
            role="resident",
            is_active=True,
        )
        db.add_all([admin, resident])
        db.commit()
    finally:
        db.close()

    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token():
    return create_access_token(data={"sub": "1", "role": "admin"})


@pytest.fixture
def resident_token():
    return create_access_token(data={"sub": "2", "role": "resident"})
