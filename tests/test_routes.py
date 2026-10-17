def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["district"] == "Barabanki, Uttar Pradesh"


def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Barabanki Connect" in response.text
    assert "Connecting People, Heritage & Commerce" in response.text


def test_about_page_renders(client):
    response = client.get("/about")
    assert response.status_code == 200
    assert "District Profile: Barabanki, Uttar Pradesh" in response.text


def test_contact_page_renders(client):
    response = client.get("/contact")
    assert response.status_code == 200
    assert "Civic Inquiries & Emergency Directory" in response.text
    assert "Police Response" in response.text


def test_news_page_renders(client):
    response = client.get("/news")
    assert response.status_code == 200
    assert "Civic News & Bulletins" in response.text


def test_events_page_renders(client):
    response = client.get("/events")
    assert response.status_code == 200
    assert "Events, Fairs & Festivals" in response.text


def test_businesses_page_renders(client):
    response = client.get("/businesses")
    assert response.status_code == 200
    assert "Business & Artisan Directory" in response.text


def test_jobs_page_renders(client):
    response = client.get("/jobs")
    assert response.status_code == 200
    assert "Local Employment & Vacancies" in response.text


def test_education_page_renders(client):
    response = client.get("/education")
    assert response.status_code == 200
    assert "Educational Institutions in Barabanki" in response.text


def test_community_page_renders(client):
    response = client.get("/community")
    assert response.status_code == 200
    assert "Citizen & Student Forum" in response.text


def test_tourism_page_renders(client):
    response = client.get("/tourism")
    assert response.status_code == 200
    assert "Historic, Spiritual & Botanical Heritage" in response.text


def test_creators_page_renders(client):
    response = client.get("/creators")
    assert response.status_code == 200
    assert "Artisans, Weavers & Creators" in response.text


def test_universal_search_page_renders(client):
    response = client.get("/search?q=Deva")
    assert response.status_code == 200
    assert "Results for" in response.text


def test_privacy_and_terms_render(client):
    p_resp = client.get("/privacy")
    assert p_resp.status_code == 200
    assert "Privacy Policy" in p_resp.text

    t_resp = client.get("/terms")
    assert t_resp.status_code == 200
    assert "Terms of Service" in t_resp.text


def test_auth_pages_render(client):
    login_resp = client.get("/auth/login")
    assert login_resp.status_code == 200
    assert "Welcome Back" in login_resp.text

    reg_resp = client.get("/auth/register")
    assert reg_resp.status_code == 200
    assert "Join Barabanki Connect" in reg_resp.text


from app.core.security import generate_csrf_token


def test_admin_routes_redirect_anonymous(client):
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code in (302, 303, 307)
    assert "/auth/login" in resp.headers["location"]


def test_admin_dashboard_accessible_with_token(client, admin_token):
    resp = client.get("/admin", cookies={"barabanki_session": admin_token})
    assert resp.status_code == 200
    assert "Administrative Dashboard" in resp.text


def test_admin_users_view_accessible_with_token(client, admin_token):
    resp = client.get("/admin/users", cookies={"barabanki_session": admin_token})
    assert resp.status_code == 200
    assert "User Accounts & Roles" in resp.text


def test_admin_moderation_view_accessible_with_token(client, admin_token):
    resp = client.get("/admin/moderation", cookies={"barabanki_session": admin_token})
    assert resp.status_code == 200
    assert "Moderation Queue & Reports" in resp.text


def test_admin_listings_view_accessible_with_token(client, admin_token):
    resp = client.get("/admin/listings", cookies={"barabanki_session": admin_token})
    assert resp.status_code == 200
    assert "Business & Vacancy Verifications" in resp.text


def test_contact_form_submission(client):
    csrf = generate_csrf_token("testclient")
    resp = client.post(
        "/contact",
        data={
            "name": "Barabanki Resident",
            "email": "resident@barabanki.in",
            "subject": "Inquiry regarding heritage bus routes",
            "message": "Are there scheduled weekend buses connecting Barabanki Junction to Parijaat Tree?",
            "csrf_token": csrf,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Your inquiry has been received" in resp.text

