"""
conftest.py is a special pytest file.
Fixtures defined here are automatically available to all test files.
We create a fresh in-memory SQLite database for each test session
so tests don't affect the real database.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app

# Use in-memory SQLite for tests - fast and disposable
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    """Replace the real DB with test DB for all requests during testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables before tests, drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def client():
    """
    TestClient simulates HTTP requests to our API.
    We override get_db so all requests use the test database.
    scope="session" means one client is shared across all tests.
    """
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def auth_headers(client):
    """
    Register and login a test user, return auth headers.
    Other tests can use this fixture to make authenticated requests.
    """
    client.post("/auth/register", params={
        "username": "testuser",
        "email": "test@test.com",
        "password": "testpass123"
    })
    response = client.post("/auth/token", data={
        "username": "testuser",
        "password": "testpass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
