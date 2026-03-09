"""Tests for analytics endpoints."""


def test_leaderboard_no_data(client):
    """Test leaderboard returns 404 when no matches exist for that competition."""
    response = client.get("/analytics/leaderboard?competition=FakeLeague&season=2099/2100")
    assert response.status_code == 404


def test_head_to_head_same_team(client):
    """Test that head to head with same team returns 400."""
    response = client.get("/analytics/head-to-head?team1_id=1&team2_id=1")
    assert response.status_code == 400


def test_head_to_head_invalid_team(client):
    """Test that head to head with non-existent team returns 404."""
    response = client.get("/analytics/head-to-head?team1_id=99999&team2_id=99998")
    assert response.status_code == 404


def test_form_invalid_team(client):
    """Test that form for non-existent team returns 404."""
    response = client.get("/analytics/form/99999")
    assert response.status_code == 404


def test_predict_same_team(client):
    """Test that predicting a team against itself returns 400."""
    response = client.get("/analytics/predict?home_team_id=1&away_team_id=1")
    assert response.status_code == 400


def test_predict_returns_probabilities(client, auth_headers):
    """Test that predict endpoint returns valid probability structure."""
    # Create two teams to predict between
    t1 = client.post("/teams/", json={"name": "Predict FC"}, headers=auth_headers).json()
    t2 = client.post("/teams/", json={"name": "Predict United"}, headers=auth_headers).json()

    response = client.get(f"/analytics/predict?home_team_id={t1['id']}&away_team_id={t2['id']}")
    assert response.status_code == 200
    data = response.json()
    assert "probabilities" in data
    assert "home_win" in data["probabilities"]
    assert "draw" in data["probabilities"]
    assert "away_win" in data["probabilities"]
    # Probabilities must sum to approximately 1
    total = sum(data["probabilities"].values())
    assert abs(total - 1.0) < 0.01
