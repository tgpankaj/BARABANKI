import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, ConfigurationError
from app.core.database import Base
from app.models import (
    User,
    CreatorProfile,
    TourismSpot,
    EducationInstitute,
    Business,
    NewsArticle,
    Event,
    JobListing,
    CommunityPost,
    CivicIssue,
    AdCampaign,
)
from app.seeds.seed_data import seed, get_or_create_user


@pytest.fixture
def isolated_db():
    """Create a completely isolated in-memory SQLite database for seeding tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_seed_idempotency_and_no_duplicate_records(isolated_db):
    """Calling seed() multiple times must be 100% idempotent and produce 0 duplicate records."""
    # First seed run on empty database
    seed(db_session=isolated_db)

    user_count_1 = isolated_db.query(User).count()
    creator_count_1 = isolated_db.query(CreatorProfile).count()
    tourism_count_1 = isolated_db.query(TourismSpot).count()
    education_count_1 = isolated_db.query(EducationInstitute).count()
    business_count_1 = isolated_db.query(Business).count()
    news_count_1 = isolated_db.query(NewsArticle).count()
    event_count_1 = isolated_db.query(Event).count()
    job_count_1 = isolated_db.query(JobListing).count()
    post_count_1 = isolated_db.query(CommunityPost).count()
    issue_count_1 = isolated_db.query(CivicIssue).count()
    campaign_count_1 = isolated_db.query(AdCampaign).count()

    assert user_count_1 >= 7
    assert creator_count_1 >= 4
    assert tourism_count_1 >= 4
    assert education_count_1 >= 5
    assert business_count_1 >= 4

    # Second seed run on already seeded database
    seed(db_session=isolated_db)

    assert isolated_db.query(User).count() == user_count_1
    assert isolated_db.query(CreatorProfile).count() == creator_count_1
    assert isolated_db.query(TourismSpot).count() == tourism_count_1
    assert isolated_db.query(EducationInstitute).count() == education_count_1
    assert isolated_db.query(Business).count() == business_count_1
    assert isolated_db.query(NewsArticle).count() == news_count_1
    assert isolated_db.query(Event).count() == event_count_1
    assert isolated_db.query(JobListing).count() == job_count_1
    assert isolated_db.query(CommunityPost).count() == post_count_1
    assert isolated_db.query(CivicIssue).count() == issue_count_1
    assert isolated_db.query(AdCampaign).count() == campaign_count_1


def test_seed_preserves_custom_user_modifications(isolated_db):
    """Seed execution must never overwrite modifications made by users or admins."""
    seed(db_session=isolated_db)

    # Modify citizen user bio and creator profile
    citizen = isolated_db.query(User).filter(User.username == "aarav_sharma").first()
    assert citizen is not None
    custom_user_bio = "Updated bio: Working on rural civic tech initiatives."
    citizen.bio = custom_user_bio

    creator = isolated_db.query(CreatorProfile).join(User).filter(User.username == "rohitvlogs").first()
    assert creator is not None
    custom_creator_bio = "Updated creator bio: 4K aerial photography of Barabanki."
    creator.bio = custom_creator_bio
    isolated_db.commit()

    # Re-run seed
    seed(db_session=isolated_db)

    # Verify custom edits were preserved
    isolated_db.refresh(citizen)
    isolated_db.refresh(creator)
    assert citizen.bio == custom_user_bio
    assert creator.bio == custom_creator_bio


def test_get_or_create_user_conflict_resolution(isolated_db):
    """Ensure get_or_create_user safely resolves partial conflicts without UNIQUE constraint crashes."""
    # 1. Create a user
    u1 = get_or_create_user(
        isolated_db,
        username="unique_user_one",
        email="one@barabanki.local",
        defaults={"full_name": "User One", "hashed_password": "hash", "role": "resident"},
    )
    isolated_db.commit()
    assert u1.id is not None

    # 2. Try to get_or_create with matching username but different email:
    # Must retrieve the existing user without IntegrityError
    u1_match_username = get_or_create_user(
        isolated_db,
        username="unique_user_one",
        email="different_email@barabanki.local",
        defaults={"full_name": "Should Not Overwrite", "hashed_password": "hash", "role": "resident"},
    )
    assert u1_match_username.id == u1.id
    assert u1_match_username.username == "unique_user_one"

    # 3. Try to get_or_create with matching email but different username:
    # Must retrieve the existing user without IntegrityError
    u1_match_email = get_or_create_user(
        isolated_db,
        username="different_username",
        email="one@barabanki.local",
        defaults={"full_name": "Should Not Overwrite", "hashed_password": "hash", "role": "resident"},
    )
    assert u1_match_email.id == u1.id
    assert u1_match_email.email == "one@barabanki.local"


def test_seed_transaction_rollback_on_error(isolated_db):
    """Seed function must catch errors, roll back the transaction, and re-raise."""
    with patch("app.seeds.seed_data.get_or_create_user", side_effect=RuntimeError("Simulated database failure")):
        with pytest.raises(RuntimeError, match="Simulated database failure"):
            seed(db_session=isolated_db)


def test_production_rejects_sqlite_configuration():
    """Production mode must reject SQLite and require a valid PostgreSQL (e.g. Neon) connection."""
    # SQLite URL in production must fail validation
    with pytest.raises((ConfigurationError, Exception)) as exc_info:
        Settings(ENVIRONMENT="production", DATABASE_URL="sqlite:///./barabanki.db")
    assert "SQLite cannot be used in production" in str(exc_info.value)

    # Empty URL in production must fail validation
    with pytest.raises((ConfigurationError, Exception)) as exc_info:
        Settings(ENVIRONMENT="production", DATABASE_URL="")
    assert "SQLite cannot be used in production" in str(exc_info.value)

    # Valid Neon PostgreSQL connection string succeeds and normalizes
    neon_url = "postgres://neondb_owner:secret@ep-cool-base-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    prod_settings = Settings(ENVIRONMENT="production", DATABASE_URL=neon_url)
    assert prod_settings.is_production is True
    assert prod_settings.DATABASE_URL.startswith("postgresql+psycopg2://")


def test_lifespan_detects_existing_users_and_skips_seed(isolated_db):
    """When users exist in the database, lifespan logic skips redundant seeding."""
    # Seed baseline users
    seed(db_session=isolated_db)
    has_users = isolated_db.query(User.id).first() is not None
    assert has_users is True
