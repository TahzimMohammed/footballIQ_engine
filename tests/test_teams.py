"""Tests for Teams CRUD endpoints."""


def test_list_teams_empty(client):
    """Test that listing teams returns 200 even when empty."""
    response = client.get("/teams/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_team_authenticated(client, auth_headers):
    """Test that an authenticated user can create a team."""
    response = client.post("/teams/", json={
        "name": "Test United",
        "country": "England",
        "stadium": "Test Stadium"
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test United"
    assert data["country"] == "England"
    assert "id" in data


def test_create_team_unauthenticated(client):
    """Test that unauthenticated user cannot create a team."""
    response = client.post("/teams/", json={"name": "Unauthorized FC"})
    assert response.status_code == 401


def test_get_team_by_id(client, auth_headers):
    """Test getting a specific team by ID."""
    # Create a team first
    create_response = client.post("/teams/", json={
        "name": "Get Test FC",
        "country": "Spain"
    }, headers=auth_headers)
    team_id = create_response.json()["id"]

    # Now get it
    response = client.get(f"/teams/{team_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Get Test FC"


def test_get_team_not_found(client):
    """Test that getting a non-existent team returns 404."""
    response = client.get("/teams/99999")
    assert response.status_code == 404


def test_update_team(client, auth_headers):
    """Test partial update of a team."""
    create_response = client.post("/teams/", json={
        "name": "Update Test FC"
    }, headers=auth_headers)
    team_id = create_response.json()["id"]

    # Only update the manager
    response = client.patch(f"/teams/{team_id}", json={
        "manager": "Pep Guardiola"
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["manager"] == "Pep Guardiola"
    # Name should be unchanged
    assert response.json()["name"] == "Update Test FC"


def test_filter_teams_by_country(client, auth_headers):
    """Test filtering teams by country."""
    client.post("/teams/", json={"name": "Germany FC", "country": "Germany"}, headers=auth_headers)

    response = client.get("/teams/?country=Germany")
    assert response.status_code == 200
    teams = response.json()
    assert all("Germany" in (t.get("country") or "") for t in teams)
