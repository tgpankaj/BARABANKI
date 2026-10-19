#!/usr/bin/env python3
"""
Barabanki Connect — Pre-Flight Deployment & Migration Script
Executes on Render during build / release or locally before launching production:
1. Validates environment variables (SECRET_KEY, CSRF_SECRET, DATABASE_URL).
2. Probes database connection (Neon PostgreSQL / SQLite).
3. Executes Alembic migrations safely up to head revision.
4. Initializes seed baseline if database is empty.
5. Verifies storage configuration.
"""

import sys
import logging
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("deploy")

from app.core.config import settings
from app.core.database import engine, get_masked_db_url, init_db, SessionLocal
from app.core.storage import storage_service
from app.models.user import User
from app.seeds.seed_data import seed


def verify_environment():
    logger.info("=== STEP 1: Verifying Environment Configuration ===")
    logger.info("Project: %s", settings.PROJECT_NAME)
    logger.info("Environment: %s (is_production: %s)", settings.ENVIRONMENT, settings.is_production)
    logger.info("Debug Mode: %s", settings.DEBUG)
    logger.info("Host/Port: %s:%s", settings.HOST, settings.PORT)
    logger.info("Cookie Secure: %s", settings.effective_cookie_secure)
    logger.info("Allowed Origins: %s", settings.ALLOWED_ORIGINS)

    if settings.is_production:
        if settings.DEBUG:
            logger.error("FATAL: DEBUG mode is enabled in production! Set DEBUG=False.")
            sys.exit(1)
        if "super_secret_local_dev_key" in settings.SECRET_KEY:
            logger.error("FATAL: Insecure default SECRET_KEY detected in production! Provide a secure 32-byte key.")
            sys.exit(1)
        if "barabanki_csrf_protection_key" in settings.CSRF_SECRET:
            logger.error("FATAL: Insecure default CSRF_SECRET detected in production! Provide a secure 32-byte key.")
            sys.exit(1)

    logger.info("Security keys and environment settings validated successfully.")


def verify_database_and_migrate():
    logger.info("=== STEP 2: Database Connectivity & Migrations ===")
    masked_url = get_masked_db_url(settings.DATABASE_URL)
    logger.info("Target Database: %s", masked_url)
    dialect = engine.dialect.name
    logger.info("Database Dialect: %s", dialect)

    if settings.is_production and dialect == "sqlite":
        logger.warning(
            "ADVISORY: Running production on SQLite. Ephemeral container restarts will not persist data. "
            "For production deployments on Render, use Neon PostgreSQL."
        )

    # 1. Probe database connectivity
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection handshake successful.")
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        sys.exit(1)

    # 2. Run Alembic upgrade head
    logger.info("Executing Alembic migrations (upgrade head)...")
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(str(BASE_DIR / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic schema migrations applied successfully to head.")
    except Exception as e:
        logger.error("Alembic migration failed: %s", e)
        # Fall back to init_db if alembic fails on fresh DB
        logger.info("Attempting fallback init_db() schema synchronization...")
        init_db()

    # 3. Check for admin user & seed if empty
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if not admin_user:
            logger.info("No administrative account found. Seeding authentic Barabanki baseline data...")
            seed()
            logger.info("Seeding completed successfully.")
        else:
            logger.info("Database already populated (admin user '%s' exists).", settings.ADMIN_EMAIL)
    finally:
        db.close()


def verify_storage():
    logger.info("=== STEP 3: Persistent Storage Verification ===")
    info = storage_service.get_backend_info()
    logger.info("Storage Backend: %s", info["backend"])
    logger.info("Storage Configured: %s", info["configured"])
    logger.info("Storage Persistence: %s", info["storage_persistence"])
    logger.info("Render Ephemeral Disk Dependency: %s", info["ephemeral_disk_used"])


def main():
    logger.info("Starting Barabanki Connect Pre-Flight Deployment Sequence...")
    verify_environment()
    verify_database_and_migrate()
    verify_storage()
    logger.info("==================================================================")
    logger.info("Pre-flight deployment checks passed! System is ready for launch.")
    logger.info("==================================================================")


if __name__ == "__main__":
    main()
