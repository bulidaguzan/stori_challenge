import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from decimal import Decimal
from routes.get_summary.get_summary import (
    router,
    verify_token,
    get_user_id_from_email,
    get_user_transactions,
    calculate_summary,
    send_summary_email,
)


# Setup test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Test data
mock_token = "valid_test_token"
mock_email = "test@example.com"
mock_user_id = "user123"

mock_transactions = [
    {
        "UserId": "user123",
        "Date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        "amount": 100.50,
    },
    {
        "UserId": "user123",
        "Date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
        "amount": -50.25,
    },
    {
        "UserId": "user123",
        "Date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
        "amount": 75.00,
    },
]

# -------------------------- Unit Tests --------------------------


@pytest.mark.asyncio
@patch("routes.get_summary.get_summary.verify_token")
@patch("routes.get_summary.get_summary.get_user_id_from_email")
@patch("routes.get_summary.get_summary.get_user_transactions")
@patch("routes.get_summary.get_summary.send_summary_email")
async def test_get_summary_success(
    mock_send_email,
    mock_get_transactions,
    mock_get_user_id,
    mock_verify_token,
):
    """Test successful summary generation and email sending"""
    # Configure mocks
    mock_verify_token.return_value = {"email": mock_email}
    mock_get_user_id.return_value = mock_user_id
    mock_get_transactions.return_value = mock_transactions
    mock_send_email.return_value = None

    # Make request
    response = client.post("/get-summary", json={"access_token": mock_token})

    # Verify response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "summary" in response.json()

    # Verify mock calls
    mock_verify_token.assert_called_once_with(mock_token)
    mock_get_user_id.assert_called_once_with(mock_email)
    mock_get_transactions.assert_called_once_with(mock_user_id)
    mock_send_email.assert_called_once()


def test_verify_token_valid():
    """Test token verification with valid token"""
    with patch("routes.get_summary.get_summary.token_table") as mock_table:
        # Configure mock
        mock_table.scan.return_value = {
            "Items": [
                {
                    "token": mock_token,
                    "email": mock_email,
                    "expiration": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                }
            ]
        }

        # Verify token
        result = verify_token(mock_token)

        assert result is not None
        assert result["token"] == mock_token
        assert result["email"] == mock_email


def test_verify_token_expired():
    """Test token verification with expired token"""
    with patch("routes.get_summary.get_summary.token_table") as mock_table:
        # Configure mock with expired token
        mock_table.scan.return_value = {
            "Items": [
                {
                    "token": mock_token,
                    "email": mock_email,
                    "expiration": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                }
            ]
        }

        # Verify token
        result = verify_token(mock_token)
        assert result is None


def test_get_user_id_from_email_success():
    """Test successful user ID retrieval"""
    with patch("routes.get_summary.get_summary.users_table") as mock_table:
        # Configure mock
        mock_table.scan.return_value = {
            "Items": [{"id": mock_user_id, "email": mock_email}]
        }

        # Get user ID
        result = get_user_id_from_email(mock_email)
        assert result == mock_user_id


def test_get_user_transactions_success():
    """Test successful transaction retrieval"""
    with patch("routes.get_summary.get_summary.movements_table") as mock_table:
        # Configure mock
        mock_table.scan.return_value = {"Items": mock_transactions}

        # Get transactions
        result = get_user_transactions(mock_user_id)
        assert len(result) == len(mock_transactions)
        assert result == mock_transactions


def test_calculate_summary_success():
    """Test summary calculation"""
    # Calculate summary
    result = calculate_summary(mock_transactions)

    # Verify calculations
    assert "total_balance" in result
    assert "transactions_by_month" in result
    assert "avg_debit" in result
    assert "avg_credit" in result
    assert result["total_balance"] == 125.25  # 100.50 - 50.25 + 75.00
    assert result["avg_debit"] == -50.25
    assert result["avg_credit"] == 87.75  # (100.50 + 75.00) / 2


@pytest.mark.asyncio
@patch("routes.get_summary.get_summary.ses_client")
async def test_send_summary_email_success(mock_ses):
    """Test successful email sending"""
    mock_ses.send_email.return_value = {"MessageId": "test123"}

    summary = {
        "total_balance": 125.25,
        "transactions_by_month": {"October": 3},
        "avg_debit": -50.25,
        "avg_credit": 87.75,
    }

    # Send email
    send_summary_email(mock_email, summary)

    # Verify email was sent
    mock_ses.send_email.assert_called_once()


# -------------------------- Error Tests --------------------------


@pytest.mark.asyncio
async def test_get_summary_invalid_token():
    """Test summary request with invalid token"""
    with patch("routes.get_summary.get_summary.verify_token") as mock_verify:
        mock_verify.return_value = None

        response = client.post("/get-summary", json={"access_token": "invalid_token"})

        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]


@pytest.mark.asyncio
@patch("routes.get_summary.get_summary.verify_token")
@patch("routes.get_summary.get_summary.get_user_id_from_email")
@patch("routes.get_summary.get_summary.get_user_transactions")
@patch(
    "routes.get_summary.get_summary.send_summary_email"
)  # Agregamos mock para send_summary_email
async def test_get_summary_no_transactions(
    mock_send_email,  # Nuevo mock
    mock_get_transactions,
    mock_get_user_id,
    mock_verify_token,
):
    """Test summary generation with no transactions"""
    # Configuramos los mocks
    mock_verify_token.return_value = {"email": "test@example.com"}
    mock_get_user_id.return_value = "test-user-id"
    mock_get_transactions.return_value = []
    mock_send_email.return_value = None  # El email se envía exitosamente

    # Realizamos la petición
    response = client.post("/get-summary", json={"access_token": "mock-token"})

    # Verificamos la respuesta
    assert response.status_code == 200
    assert response.json()["summary"]["total_balance"] == 0
    assert response.json()["summary"]["avg_debit"] == 0
    assert response.json()["summary"]["avg_credit"] == 0

    # Verificamos que se llamó a send_summary_email
    mock_send_email.assert_called_once()


# -------------------------- Integration Tests --------------------------


@pytest.mark.integration
@patch("routes.get_summary.get_summary.token_table")
@patch("routes.get_summary.get_summary.users_table")
@patch("routes.get_summary.get_summary.movements_table")
@patch("routes.get_summary.get_summary.ses_client")
async def test_get_summary_full_flow(
    mock_ses,
    mock_movements_table,
    mock_users_table,
    mock_token_table,
):
    """Test complete summary generation flow"""
    # Configure all mocks
    mock_token_table.scan.return_value = {
        "Items": [
            {
                "token": mock_token,
                "email": mock_email,
                "expiration": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            }
        ]
    }

    mock_users_table.scan.return_value = {
        "Items": [{"id": mock_user_id, "email": mock_email}]
    }

    mock_movements_table.scan.return_value = {"Items": mock_transactions}

    mock_ses.send_email.return_value = {"MessageId": "test123"}

    # Make request
    response = client.post("/get-summary", json={"access_token": mock_token})

    # Verify complete flow
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "summary" in response.json()
    assert mock_ses.send_email.called


# -------------------------- Test Fixtures --------------------------


@pytest.fixture
def mock_aws_services():
    """Fixture for AWS services"""
    with patch("routes.get_summary.get_summary.token_table") as mock_token_table, patch(
        "routes.get_summary.get_summary.users_table"
    ) as mock_users_table, patch(
        "routes.get_summary.get_summary.movements_table"
    ) as mock_movements_table, patch(
        "routes.get_summary.get_summary.ses_client"
    ) as mock_ses:
        yield {
            "token_table": mock_token_table,
            "users_table": mock_users_table,
            "movements_table": mock_movements_table,
            "ses_client": mock_ses,
        }
