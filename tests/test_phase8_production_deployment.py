import pytest
from app.core.config import Settings
from app.core.database import get_masked_db_url
from app.core.storage import (
    validate_upload_metadata,
    sanitize_filename,
    validate_hosted_image_url,
    storage_service,
    ALLOWED_EXTENSIONS,
)


def test_database_url_normalization_for_neon_and_render():
    """Verify that postgres:// schemes provided by Neon/Render are automatically normalized to postgresql+psycopg2://"""
    neon_url = "postgres://neondb_owner:npg_SecretPass123@ep-cool-base-123456.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    normalized = Settings.normalize_database_url(neon_url)
    assert normalized.startswith("postgresql+psycopg2://")
    assert "sslmode=require" in normalized
    assert "npg_SecretPass123" in normalized

    # Direct postgresql:// also normalized to explicit psycopg2 driver
    standard_pg = "postgresql://user:pass@localhost:5432/testdb"
    assert Settings.normalize_database_url(standard_pg) == "postgresql+psycopg2://user:pass@localhost:5432/testdb"

    # SQLite URL preserved
    sqlite_url = "sqlite:///./barabanki.db"
    assert Settings.normalize_database_url(sqlite_url) == sqlite_url


def test_get_masked_db_url_masks_credentials():
    """Ensure database passwords are never leaked in logs, metrics, or error output."""
    raw_url = "postgresql+psycopg2://barabanki_user:UltraSecretPass998@ep-cool-base.neon.tech/barabanki_db?sslmode=require"
    masked = get_masked_db_url(raw_url)
    assert "UltraSecretPass998" not in masked
    assert ":****@" in masked
    assert "barabanki_user" in masked
    assert "ep-cool-base.neon.tech" in masked


def test_allowed_origins_parsing_flexibility():
    """Verify that ALLOWED_ORIGINS parses both JSON string arrays and comma-separated lists."""
    # JSON array string
    json_origins = '["https://barabanki-connect.onrender.com", "https://barabanki-connect.in"]'
    parsed_json = Settings.parse_allowed_origins(json_origins)
    assert isinstance(parsed_json, list)
    assert len(parsed_json) == 2
    assert "https://barabanki-connect.onrender.com" in parsed_json

    # Comma-separated list string
    csv_origins = "https://barabanki-connect.onrender.com, https://barabanki.up.gov.in"
    parsed_csv = Settings.parse_allowed_origins(csv_origins)
    assert isinstance(parsed_csv, list)
    assert len(parsed_csv) == 2
    assert "https://barabanki.up.gov.in" in parsed_csv


def test_persistent_storage_metadata_validation():
    """Verify upload metadata validation prevents path traversal and enforces file constraints."""
    # 1. Valid image metadata
    valid, err = validate_upload_metadata("banner.jpg", "image/jpeg", 1024 * 500)
    assert valid is True
    assert err == ""

    valid, err = validate_upload_metadata("logo.webp", "image/webp", 2 * 1024 * 1024)
    assert valid is True

    # 2. Path traversal attempts rejected
    valid, err = validate_upload_metadata("../../../etc/passwd.jpg", "image/jpeg", 100)
    assert valid is False
    assert "directory traversal" in err

    # 3. Disallowed extensions rejected
    valid, err = validate_upload_metadata("exploit.php", "image/jpeg", 500)
    assert valid is False
    assert "Unsupported file extension" in err

    valid, err = validate_upload_metadata("malware.exe", "application/octet-stream", 500)
    assert valid is False

    # 4. MIME type mismatch
    valid, err = validate_upload_metadata("image.png", "image/jpeg", 500)
    assert valid is False
    assert "does not match" in err

    # 5. Oversized files rejected (limit 5MB)
    valid, err = validate_upload_metadata("huge_photo.jpg", "image/jpeg", 10 * 1024 * 1024)
    assert valid is False
    assert "exceeds" in err


def test_safe_uuid_filename_generation():
    """Verify sanitize_filename outputs collision-resistant UUIDs with sanitized extensions."""
    out1 = sanitize_filename("my holiday photo (1).jpeg")
    assert out1.endswith(".jpeg")
    assert " " not in out1
    assert len(out1) == 32 + 5  # 32 hex chars + .jpeg

    out2 = sanitize_filename("../../malicious_path/test.PNG")
    assert out2.endswith(".png")
    assert "/" not in out2
    assert "\\" not in out2
    assert ".." not in out2


def test_validate_hosted_image_url():
    """Verify URL validation allows safe domains and rejects dangerous protocols."""
    # Safe HTTPS URL
    valid, err, cleaned = validate_hosted_image_url("https://images.unsplash.com/photo-1548013146-72479768bada")
    assert valid is True
    assert cleaned.startswith("https://")

    # Safe relative static path
    valid, err, cleaned = validate_hosted_image_url("/static/images/hero-banner.jpg")
    assert valid is True
    assert cleaned == "/static/images/hero-banner.jpg"

    # Reject dangerous protocols
    valid, err, _ = validate_hosted_image_url("javascript:alert('xss')")
    assert valid is False
    assert "Unsafe URL scheme" in err

    valid, err, _ = validate_hosted_image_url("//phishing-site.com/login.jpg")
    assert valid is False
    assert "Protocol-relative" in err


def test_storage_service_reports_ephemeral_independence():
    """Verify that default storage architecture does not rely on Render's ephemeral disk."""
    info = storage_service.get_backend_info()
    assert info["ephemeral_disk_used"] is False
    assert info["storage_persistence"] == "permanent"


def test_production_smoke_test_suite_against_testclient(client):
    """Run all core smoke checks through the ASGI TestClient to verify routing, health, and headers."""
    # 1. Health Probe
    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    health_data = resp_health.json()
    assert health_data["status"] == "healthy"
    assert health_data["database"] == "connected"

    # 2. Homepage & Headers
    resp_home = client.get("/")
    assert resp_home.status_code == 200
    assert "Barabanki Connect" in resp_home.text
    assert resp_home.headers.get("x-content-type-options") == "nosniff"

    # 3. Static CSS
    resp_css = client.get("/static/css/style.css")
    assert resp_css.status_code == 200
    assert "public" in resp_css.headers.get("cache-control", "")

    # 4. Active Ads API
    resp_ads = client.get("/api/v1/ads/active")
    assert resp_ads.status_code == 200
    assert isinstance(resp_ads.json(), list)

    # 5. Protected Route Authorization Boundary
    resp_admin = client.get("/admin", follow_redirects=False)
    assert resp_admin.status_code in (302, 303)
    assert "/auth/login" in resp_admin.headers.get("location", "")

    # 6. Custom 404
    resp_404 = client.get("/route-that-does-not-exist-smoke-test-404")
    assert resp_404.status_code == 404
