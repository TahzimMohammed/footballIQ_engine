"""
Tests for authentication endpoints.
Each function starting with test_ is automatically run by pytest.
"""


def test_register_success(client):
    """Test that a new user can register successfully."""
    response = client.post("/auth/register", params={
        "username": "newuser",
        "email": "new@test.com",
        "password": "password123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@test.com"
    assert "password" not in data  # Password must never be in response


def test_register_duplicate_username(client):
    """Test that registering with an existing username returns 400."""
    client.post("/auth/register", params={
        "username": "duplicate",
        "email": "dup1@test.com",
        "password": "pass123"
    })
    response = client.post("/auth/register", params={
        "username": "duplicate",
        "email": "dup2@test.com",
        "password": "pass123"
    })
    assert response.status_code == 400


def test_login_success(client):
    """Test that a registered user can login and get a JWT token."""
    client.post("/auth/register", params={
        "username": "loginuser",
        "email": "login@test.com",
        "password": "password123"
    })
    response = client.post("/auth/token", data={
        "username": "loginuser",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # JWT tokens start with eyJ
    assert data["access_token"].startswith("eyJ")


def test_login_wrong_password(client):
    """Test that wrong password returns 401."""
    response = client.post("/auth/token", data={
        "username": "testuser",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_protected_endpoint_without_token(client):
    """Test that protected endpoints reject requests without a token."""
    response = client.post("/teams/", json={"name": "Test FC"})
    assert response.status_code == 401
