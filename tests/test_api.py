def test_api_get_news(client):
    response = client.get("/api/v1/news")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_get_events(client):
    response = client.get("/api/v1/events")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_get_businesses(client):
    response = client.get("/api/v1/businesses")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_get_jobs(client):
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_get_education(client):
    response = client.get("/api/v1/education")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_get_tourism(client):
    response = client.get("/api/v1/tourism")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_community_post_creation(client, resident_token):
    payload = {
        "title": "Student study group for UP Polytechnic exams in Nawabganj",
        "category": "Student Hub",
        "content": "Let's organize weekend study circles at the municipal library for students preparing for technical diplomas.",
    }
    response = client.post(
        "/api/v1/community/posts",
        json=payload,
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["upvotes"] == 1


def test_api_admin_stats_unauthorized(client):
    response = client.get("/api/v1/admin/stats")
    assert response.status_code in [401, 403]


def test_api_admin_stats_forbidden_for_resident(client, resident_token):
    response = client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert response.status_code == 403


def test_api_admin_stats_success_for_admin(client, admin_token):
    response = client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "businesses" in data
