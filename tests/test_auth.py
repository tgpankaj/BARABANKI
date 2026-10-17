from app.core.security import verify_password, get_password_hash


def test_password_hashing():
    raw_password = "SecureBarabankiPassword2026!"
    hashed = get_password_hash(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False


def test_api_user_registration(client):
    payload = {
        "username": "shreya_bbk",
        "email": "shreya@barabanki.local",
        "full_name": "Shreya Verma",
        "password": "Password123!",
        "role": "resident",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "shreya_bbk"
    assert data["email"] == "shreya@barabanki.local"
    assert "hashed_password" not in data


def test_api_duplicate_registration(client):
    payload = {
        "username": "shreya_bbk",
        "email": "shreya@barabanki.local",
        "full_name": "Shreya Verma Duplicate",
        "password": "Password123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400


def test_api_token_login_success(client):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin@test.local", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_api_token_login_failure(client):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin@test.local", "password": "IncorrectPassword!"},
    )
    assert response.status_code == 401


def test_api_get_current_user_profile(client, resident_token):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "resident"
