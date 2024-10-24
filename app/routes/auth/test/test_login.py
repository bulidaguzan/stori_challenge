import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from jose import jwt
from fastapi import FastAPI, HTTPException

# Imports
from routes.auth.login import (
    router,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from routes.auth.models import LoginRequest

# Setup test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Test data
valid_user_data = {"email": "test@example.com", "password": "valid_password"}

mock_user = {
    "email": "test@example.com",
    "password_hash": "hashed_password",
    "name": "Test User",
}

# -------------------------- Unit Tests --------------------------


def test_create_access_token():
    """Test token creation with valid data"""
    data = {"sub": "test@example.com"}
    token, expire = create_access_token(data)

    # Decode token to verify contents
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert decoded["sub"] == "test@example.com"
    assert isinstance(expire, datetime)
    assert expire > datetime.utcnow()
    assert expire < datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES + 1
    )


@pytest.mark.asyncio
@patch("routes.auth.login.verify_user")
@patch("routes.auth.login.save_token")
async def test_login_success(mock_save_token, mock_verify_user):
    """Test successful login flow"""
    # Configure mocks
    mock_verify_user.return_value = mock_user
    mock_save_token.return_value = None

    # Make login request
    response = client.post("/login", json=valid_user_data)

    # Verify response
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

    # Verify mock calls
    mock_verify_user.assert_called_once()
    mock_save_token.assert_called_once()


@pytest.mark.asyncio
@patch("routes.auth.login.verify_user")
async def test_login_invalid_credentials(mock_verify_user):
    """Test login with invalid credentials"""
    # Configure mock to simply return None for invalid credentials
    mock_verify_user.return_value = None

    # Make login request
    response = client.post(
        "/login", json={"email": "wrong@example.com", "password": "wrong_password"}
    )

    # Verify response
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

    # Verify mock was called
    mock_verify_user.assert_called_once()


@pytest.mark.asyncio
@patch("routes.auth.login.verify_user")
async def test_login_internal_error(mock_verify_user):
    """Test login with server error"""
    # Configure mock to raise exception
    mock_verify_user.side_effect = Exception("Database connection error")

    # Make login request
    response = client.post("/login", json=valid_user_data)

    # Verify response
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"


def test_token_expiration():
    """Test that created tokens have correct expiration time"""
    data = {"sub": "test@example.com"}

    # Capturamos el tiempo actual antes de crear el token
    current_time = datetime.utcnow()
    token, expire = create_access_token(data)

    # Decode token
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    # Convertimos la expiración del token a UTC para comparar correctamente
    token_exp = datetime.utcfromtimestamp(decoded["exp"])
    expected_exp = current_time + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Permitimos una tolerancia de 5 segundos para la creación del token
    assert abs((token_exp - expected_exp).total_seconds()) < 5


# -------------------------- Test Fixtures --------------------------


@pytest.fixture
def mock_db_session():
    """Fixture for database session"""
    session = MagicMock()
    return session


@pytest.fixture
def mock_token_blacklist():
    """Fixture for token blacklist"""
    blacklist = set()
    return blacklist
