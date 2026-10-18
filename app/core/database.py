import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)


def utc_now():
    """Return timezone-naive UTC timestamp for database column defaults without deprecation."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


db_url = settings.DATABASE_URL

# Configure engine based on dialect
if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    engine = create_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session and safely closes it."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_safe_migrations(target_engine=None):
    """Safely apply idempotent column additions for existing SQLite databases without schema resets."""
    eng = target_engine or engine
    if eng.dialect.name == "sqlite":
        with eng.connect() as conn:
            def get_columns(table_name):
                try:
                    res = conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
                    return [row[1] for row in res]
                except Exception:
                    return []

            # users table
            user_cols = get_columns("users")
            if user_cols and "locality" not in user_cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN locality VARCHAR(100) DEFAULT 'Barabanki'")
                conn.commit()

            # community_posts table
            post_cols = get_columns("community_posts")
            if post_cols and "image_url" not in post_cols:
                conn.exec_driver_sql("ALTER TABLE community_posts ADD COLUMN image_url VARCHAR(500)")
                conn.commit()

            # events table
            event_cols = get_columns("events")
            if event_cols and "capacity" not in event_cols:
                conn.exec_driver_sql("ALTER TABLE events ADD COLUMN capacity INTEGER")
                conn.commit()

            # reports table
            report_cols = get_columns("reports")
            if report_cols:
                if "moderator_id" not in report_cols:
                    conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN moderator_id INTEGER REFERENCES users(id)")
                    conn.commit()
                if "moderator_notes" not in report_cols:
                    conn.exec_driver_sql("ALTER TABLE reports ADD COLUMN moderator_notes TEXT")
                    conn.commit()


def init_db():
    """Create all tables in the database if they do not exist."""
    # Import all models to ensure they are registered with Base.metadata
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    run_safe_migrations(engine)
    logger.info("Database tables initialized successfully.")

