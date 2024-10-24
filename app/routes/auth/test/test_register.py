import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from routes.auth.register import router
from routes.auth.models import UserCreate

# Setup test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Test data
valid_user_data = {
    "email": "test@example.com",
    "password": "strongPassword123",
    "name": "Test User",
}

# -------------------------- Unit Tests --------------------------


@pytest.mark.asyncio
@patch("routes.auth.register.get_user_by_email")
@patch("routes.auth.register.create_user")
async def test_register_success(mock_create_user, mock_get_user):
    """Test successful user registration"""
    # Configure mocks
    mock_get_user.return_value = None  # Usuario no existe
    mock_create_user.return_value = None

    # Make register request
    response = client.post("/register", json=valid_user_data)

    # Verify response
    assert response.status_code == 200
    assert response.json()["email"] == valid_user_data["email"]
    assert response.json()["name"] == valid_user_data["name"]
    assert "password" in response.json()
    assert (
        response.json()["password"]
        == "Save into database, and encrypt for your security."
    )

    # Verify mock calls
    mock_get_user.assert_called_once_with(valid_user_data["email"])
    mock_create_user.assert_called_once()


@pytest.mark.asyncio
@patch("routes.auth.register.get_user_by_email")
async def test_register_existing_user(mock_get_user):
    """Test registration with existing email"""
    # Configure mock to return existing user
    mock_get_user.return_value = {
        "email": valid_user_data["email"],
        "password_hash": "hashed_password",
        "name": "Existing User",
    }

    # Make register request
    response = client.post("/register", json=valid_user_data)

    # Verify response
    assert response.status_code == 200
    assert response.json()["message"] == "User already exist"

    # Verify mock calls
    mock_get_user.assert_called_once_with(valid_user_data["email"])


@pytest.mark.asyncio
@patch("routes.auth.register.get_user_by_email")
async def test_register_database_error(mock_get_user):
    """Test registration with database error"""
    # Configure mock to raise exception
    mock_get_user.side_effect = Exception("Database connection error")

    # Make register request
    response = client.post("/register", json=valid_user_data)

    # Verify response
    assert response.status_code == 500
    assert response.json()["detail"] == "An unexpected error occurred"


@pytest.mark.asyncio
@patch("routes.auth.register.get_user_by_email")
@patch("routes.auth.register.create_user")
async def test_register_password_hashing(mock_create_user, mock_get_user):
    """Test that password is properly hashed before storage"""
    # Configure mocks
    mock_get_user.return_value = None
    mock_create_user.return_value = None

    # Make register request
    response = client.post("/register", json=valid_user_data)

    # Verify password was hashed
    assert response.status_code == 200

    # Get the UserCreate object passed to create_user
    called_user = mock_create_user.call_args[0][0]
    assert isinstance(called_user, UserCreate)
    assert (
        called_user.password != valid_user_data["password"]
    )  # Password should be hashed
    assert len(called_user.password) > len(
        valid_user_data["password"]
    )  # Hashed password is longer


# -------------------------- Integration Tests --------------------------


@pytest.mark.integration
@patch("routes.auth.register.get_user_by_email")
@patch("routes.auth.register.create_user")
async def test_register_full_flow(mock_create_user, mock_get_user):
    """Test complete registration flow"""
    # Configure mocks
    mock_get_user.return_value = None
    mock_create_user.return_value = None

    # Test data
    test_user = {
        "email": "integration@test.com",
        "password": "TestPassword123",
        "name": "Integration Test",
    }

    # Make register request
    response = client.post("/register", json=test_user)

    # Verify response
    assert response.status_code == 200
    assert response.json()["email"] == test_user["email"]
    assert response.json()["name"] == test_user["name"]

    # Verify user creation
    created_user = mock_create_user.call_args[0][0]
    assert created_user.email == test_user["email"]
    assert created_user.name == test_user["name"]
    assert created_user.password != test_user["password"]  # Password should be hashed


# -------------------------- Test Fixtures --------------------------


@pytest.fixture
def valid_user():
    """Fixture for valid user data"""
    return UserCreate(
        email="fixture@test.com", password="FixturePassword123", name="Fixture User"
    )
