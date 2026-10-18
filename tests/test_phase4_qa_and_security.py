import pytest
import sqlite3
import tempfile
from pathlib import Path
from app.core.rate_limiter import check_rate_limit, clear_rate_limits
from scripts.db_backup_restore import backup_sqlite, restore_sqlite


# ==============================================================================
# 1. SECURITY HEADERS & CONTENT SECURITY POLICY (CSP)
# ==============================================================================

def test_security_headers_present(client):
    """Responses must contain essential security hardening headers."""
    resp = client.get("/")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "SAMEORIGIN"
    assert "1; mode=block" in headers.get("x-xss-protection", "")
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "geolocation=" in headers.get("permissions-policy", "")
    assert "default-src" in headers.get("content-security-policy", "")
    assert "script-src" in headers.get("content-security-policy", "")


def test_static_asset_caching_headers(client):
    """Static assets must serve Cache-Control headers to optimize client performance."""
    resp = client.get("/static/css/style.css")
    assert resp.status_code == 200
    cache_control = resp.headers.get("cache-control", "")
    assert "public" in cache_control
    assert "max-age=" in cache_control


# ==============================================================================
# 2. SYSTEM HEALTH CHECK & ACTIVE DATABASE CONNECTIVITY
# ==============================================================================

def test_health_check_with_db_probe(client):
    """Health check must perform an active database probe and report healthy status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["district"] == "Barabanki, Uttar Pradesh"
    assert "environment" in data


# ==============================================================================
# 3. GLOBAL ERROR HANDLERS (404 & 500)
# ==============================================================================

def test_custom_404_handler_for_html_and_api(client):
    """Custom 404 handler returns clean HTML for browsers and clean JSON for APIs."""
    # HTML request
    resp_html = client.get("/non-existent-page-route-404")
    assert resp_html.status_code == 404
    assert "Page Not Found" in resp_html.text
    assert "Return to Barabanki Connect Home" in resp_html.text

    # API request
    resp_api = client.get("/api/v1/non-existent-endpoint-404")
    assert resp_api.status_code == 404
    assert resp_api.headers.get("content-type") == "application/json"
    assert resp_api.json()["detail"] == "API endpoint not found."


# ==============================================================================
# 4. CSRF VALIDATION ON AUTHENTICATION
# ==============================================================================

def test_login_rejects_missing_csrf(client):
    """Login attempt without valid CSRF token is rejected with 400 Bad Request."""
    resp = client.post(
        "/auth/login",
        data={"email_or_username": "admin@barabanki.local", "password": "AnyPassword123!"},
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert "Invalid CSRF security token" in resp.text


def test_register_rejects_missing_csrf(client):
    """Registration attempt without valid CSRF token is rejected with 400 Bad Request."""
    resp = client.post(
        "/auth/register",
        data={
            "full_name": "Unverified User",
            "username": "unverified",
            "email": "unverified@test.local",
            "password": "Password123!",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert "Invalid security token" in resp.text


# ==============================================================================
# 5. RATE LIMITING ENGINE
# ==============================================================================

def test_rate_limiter_throttles_burst_requests():
    """Rate limiter enforces request limits per client IP and triggers 429."""
    clear_rate_limits()

    class FakeRequest:
        def __init__(self, ip):
            self.headers = {}
            self.client = type("Client", (), {"host": ip})()

    req = FakeRequest("192.168.1.100")

    # Under limit (3 requests with max 3)
    assert check_rate_limit(req, scope="test_auth", max_requests=3, window_seconds=60) is True
    assert check_rate_limit(req, scope="test_auth", max_requests=3, window_seconds=60) is True
    assert check_rate_limit(req, scope="test_auth", max_requests=3, window_seconds=60) is True

    # 4th request exceeds limit -> raises HTTPException(429)
    with pytest.raises(Exception) as excinfo:
        check_rate_limit(req, scope="test_auth", max_requests=3, window_seconds=60)
    assert "429" in str(excinfo.value)

    # Different IP should not be blocked
    other_req = FakeRequest("192.168.1.101")
    assert check_rate_limit(other_req, scope="test_auth", max_requests=3, window_seconds=60) is True

    clear_rate_limits()


# ==============================================================================
# 6. ACCESSIBILITY & INCLUSIVE DESIGN
# ==============================================================================

def test_accessibility_skip_link_present(client):
    """The root page must include an accessibility skip link for keyboard & screen readers."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'class="skip-link"' in resp.text
    assert 'href="#main-content"' in resp.text
    assert "Skip to main content" in resp.text


# ==============================================================================
# 7. SQL INJECTION RESILIENCE
# ==============================================================================

def test_sql_injection_resilience_in_search(client):
    """Universal search and category filtering must be resilient against SQL injection vectors."""
    sqli_payloads = [
        "' OR '1'='1",
        "admin'--",
        "'; DROP TABLE users; --",
        "' UNION SELECT id, username, hashed_password FROM users --",
    ]

    for payload in sqli_payloads:
        resp = client.get(f"/search?q={payload}")
        assert resp.status_code == 200
        # Check that page renders without crashing or revealing database errors
        assert "Search Barabanki Connect" in resp.text

        resp_issues = client.get(f"/issues?q={payload}")
        assert resp_issues.status_code == 200


# ==============================================================================
# 8. PRIVACY & SENSITIVE CREDENTIAL ISOLATION
# ==============================================================================

def test_password_hashes_never_leaked_in_apis(client, resident_token):
    """Public endpoints and current user endpoints must never expose password hashes."""
    # 1. /api/v1/auth/me
    resp_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {resident_token}"})
    assert resp_me.status_code == 200
    me_data = resp_me.json()
    assert "hashed_password" not in me_data
    assert "password" not in me_data

    # 2. Public profile endpoint
    resp_user = client.get("/api/v1/users/test_admin")
    assert resp_user.status_code == 200
    user_data = resp_user.json()
    assert "hashed_password" not in user_data
    assert "password" not in user_data
    assert "email" not in user_data
    assert "phone" not in user_data


# ==============================================================================
# 9. DATABASE BACKUP AND RESTORATION UTILITY VERIFICATION
# ==============================================================================

def test_database_backup_and_restore_cycle():
    """Verify that hot backup and restoration cycle works cleanly with integrity verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "source_test.db"

        # Create sample database with data
        conn = sqlite3.connect(str(tmp_db))
        conn.execute("CREATE TABLE sample_data (id INTEGER PRIMARY KEY, note TEXT)")
        conn.execute("INSERT INTO sample_data (note) VALUES ('Authentic District Record')")
        conn.commit()
        conn.close()

        # Perform hot backup
        backup_file = backup_sqlite(tmp_db)
        assert backup_file.exists()
        assert backup_file.stat().st_size > 0

        # Simulate data corruption / loss on target
        restore_target = Path(tmpdir) / "restored_test.db"
        success = restore_sqlite(backup_file, restore_target)
        assert success is True
        assert restore_target.exists()

        # Verify restored data
        verify_conn = sqlite3.connect(str(restore_target))
        res = verify_conn.execute("SELECT note FROM sample_data WHERE id=1").fetchone()
        verify_conn.close()
        assert res is not None
        assert res[0] == "Authentic District Record"

        # Clean up generated backup file
        if backup_file.exists():
            backup_file.unlink()
