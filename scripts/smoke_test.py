#!/usr/bin/env python3
"""
Barabanki Connect — Automated Production Smoke Test Suite
Can execute against local development or live deployed service on Render:
    python scripts/smoke_test.py --url http://127.0.0.1:8000
    python scripts/smoke_test.py --url https://barabanki-connect.onrender.com
"""

import sys
import argparse
import httpx


def run_smoke_tests(base_url: str):
    base_url = base_url.rstrip("/")
    print(f"\n==================================================================")
    print(f" Barabanki Connect — Production Smoke Test Runner")
    print(f" Target Service: {base_url}")
    print(f"==================================================================\n")

    client = httpx.Client(timeout=15.0, follow_redirects=False)
    passed = 0
    failed = 0

    def test(name: str, check_fn):
        nonlocal passed, failed
        try:
            check_fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1

    # 1. Health check with database connectivity
    def check_health():
        r = client.get(f"{base_url}/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert data.get("status") == "healthy", f"Status degraded: {data}"
        assert data.get("database") == "connected", f"Database unreachable: {data}"
        assert "Barabanki" in data.get("district", ""), "District metadata missing"

    test("System Health & Database Connectivity Probe (/health)", check_health)

    # 2. Homepage & SEO
    def check_homepage():
        r = client.get(f"{base_url}/")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert "Barabanki Connect" in r.text, "Branding missing on homepage"
        assert "<meta name=\"description\"" in r.text, "SEO description meta missing"

    test("Portal Homepage & Brand Shell (/)", check_homepage)

    # 3. Security Headers
    def check_security_headers():
        r = client.get(f"{base_url}/")
        h = r.headers
        assert h.get("x-content-type-options") == "nosniff", "Missing X-Content-Type-Options"
        assert h.get("x-frame-options") == "SAMEORIGIN", "Missing X-Frame-Options"
        assert "content-security-policy" in h, "Missing Content-Security-Policy header"
        assert "referrer-policy" in h, "Missing Referrer-Policy"

    test("Production HTTP Security Headers", check_security_headers)

    # 4. Static Asset Caching
    def check_static_caching():
        r = client.get(f"{base_url}/static/css/style.css")
        assert r.status_code == 200, f"Static CSS returned {r.status_code}"
        assert "cache-control" in r.headers, "Cache-Control missing on static asset"
        assert "max-age=" in r.headers["cache-control"], "Cache-Control max-age missing"

    test("Static Asset Delivery & Browser Cache-Control (/static/css/style.css)", check_static_caching)

    # 5. Core Public Directories & Civic Pages
    routes = [
        ("/about", "About Barabanki"),
        ("/contact", "Contact"),
        ("/news", "News"),
        ("/events", "Events"),
        ("/businesses", "Business"),
        ("/jobs", "Jobs"),
        ("/education", "Education"),
        ("/community", "Community"),
        ("/tourism", "Heritage"),
        ("/creators", "Creators"),
        ("/advertising/policy", "Advertising Policies"),
    ]

    for path, expected_text in routes:
        def make_check(p=path, t=expected_text):
            def c():
                r = client.get(f"{base_url}{p}")
                assert r.status_code == 200, f"Expected 200 on {p}, got {r.status_code}"
                assert t.lower() in r.text.lower(), f"Expected content '{t}' missing from {p}"
            return c

        test(f"Public Page Route: {path}", make_check())

    # 6. Active Public Ads API
    def check_ads_api():
        r = client.get(f"{base_url}/api/v1/ads/active")
        assert r.status_code == 200, f"Ads API returned {r.status_code}"
        assert isinstance(r.json(), list), "Ads API should return an array"

    test("Active Advertisements REST API (/api/v1/ads/active)", check_ads_api)

    # 7. Protected Route Authorization Boundary
    def check_auth_boundary():
        for protected_path in ["/admin", "/advertiser"]:
            r = client.get(f"{base_url}{protected_path}")
            assert r.status_code in (302, 303), f"Anonymous {protected_path} should redirect, got {r.status_code}"
            assert "/auth/login" in r.headers.get("location", ""), f"{protected_path} did not redirect to login"

    test("Administrative & Advertiser Authorization Boundary Guard", check_auth_boundary)

    # 8. Custom 404 Exception Handler
    def check_404():
        r = client.get(f"{base_url}/non-existent-smoke-test-404-url")
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        assert "Page Not Found" in r.text or "404" in r.text, "Custom 404 template missing"

    test("Custom 404 Error Handler Resilience", check_404)

    # Summary
    print(f"\n------------------------------------------------------------------")
    print(f" Smoke Test Results: {passed} passed, {failed} failed.")
    print(f"------------------------------------------------------------------\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Barabanki Connect Smoke Test Runner")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of application to test")
    args = parser.parse_args()
    run_smoke_tests(args.url)
