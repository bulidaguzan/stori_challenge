import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, UploadFile
from datetime import datetime, timedelta
import io
from botocore.exceptions import ClientError
from routes.upload_file.upload_file import router

# Setup test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Test data
valid_token = "valid_test_token"
expired_token = "expired_test_token"
test_file_content = f"{valid_token}\nDate,Transaction,Amount\n2024-01-01,Payment,100.00"
test_file_name = "test_transactions.csv"

# -------------------------- Helper Functions --------------------------


def create_test_file(content: str = test_file_content):
    """Create a test file for upload"""
    return io.BytesIO(content.encode())


# -------------------------- Unit Tests --------------------------


def test_verify_token_valid():
    """Test token verification with valid token"""
    with patch("routes.upload_file.upload_file.token_table") as mock_table:
        # Configure mock for valid token
        mock_table.scan.return_value = {
            "Items": [
                {
                    "token": valid_token,
                    "expiration": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                }
            ]
        }

        from routes.upload_file.upload_file import verify_token

        result = verify_token(valid_token)
        assert result is True


def test_verify_token_expired():
    """Test token verification with expired token"""
    with patch("routes.upload_file.upload_file.token_table") as mock_table:
        # Configure mock for expired token
        mock_table.scan.return_value = {
            "Items": [
                {
                    "token": expired_token,
                    "expiration": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                }
            ]
        }

        from routes.upload_file.upload_file import verify_token

        result = verify_token(expired_token)
        assert result is False


def test_verify_token_not_found():
    """Test token verification with non-existent token"""
    with patch("routes.upload_file.upload_file.token_table") as mock_table:
        # Configure mock for non-existent token
        mock_table.scan.return_value = {"Items": []}

        from routes.upload_file.upload_file import verify_token

        result = verify_token("non_existent_token")
        assert result is False


@pytest.mark.asyncio
@patch("routes.upload_file.upload_file.verify_token")
@patch("routes.upload_file.upload_file.s3_client")
async def test_upload_file_success(mock_s3, mock_verify_token):
    """Test successful file upload"""
    # Configure mocks
    mock_verify_token.return_value = True
    mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    # Create test file
    test_file = create_test_file()

    # Make upload request
    files = {"file": (test_file_name, test_file, "text/csv")}
    response = client.post("/upload-file", files=files)

    # Verify response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["file_name"] == test_file_name

    # Verify S3 upload was called
    mock_s3.put_object.assert_called_once()


@pytest.mark.asyncio
@patch("routes.upload_file.upload_file.verify_token")
@patch("routes.upload_file.upload_file.s3_client")
async def test_upload_file_with_folder(mock_s3, mock_verify_token):
    """Test file upload with folder specification"""
    # Configure mocks
    mock_verify_token.return_value = True
    mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    # Create test file
    test_file = create_test_file()
    test_folder = "test_folder"

    # Make upload request
    files = {"file": (test_file_name, test_file, "text/csv")}
    response = client.post(f"/upload-file?folder={test_folder}", files=files)

    # Verify response
    assert response.status_code == 200
    assert response.json()["s3_path"] == f"{test_folder}/{test_file_name}"


@pytest.mark.asyncio
async def test_upload_empty_file():
    """Test upload of empty file"""
    # Create empty file
    empty_file = create_test_file(f"{valid_token}\n")

    # Make upload request
    files = {"file": (test_file_name, empty_file, "text/csv")}
    response = client.post("/upload-file", files=files)

    # Verify response
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


@pytest.mark.asyncio
@patch("routes.upload_file.upload_file.verify_token")
async def test_upload_file_invalid_token(mock_verify_token):
    """Test file upload with invalid token"""
    # Configure mock
    mock_verify_token.return_value = False

    # Create test file
    test_file = create_test_file()

    # Make upload request
    files = {"file": (test_file_name, test_file, "text/csv")}
    response = client.post("/upload-file", files=files)

    # Verify response
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


@pytest.mark.asyncio
@patch("routes.upload_file.upload_file.verify_token")
@patch("routes.upload_file.upload_file.s3_client")
async def test_upload_file_s3_error(mock_s3, mock_verify_token):
    """Test file upload with S3 error"""
    # Configure mocks
    mock_verify_token.return_value = True
    mock_s3.put_object.side_effect = ClientError(
        {"Error": {"Code": "InternalError", "Message": "S3 Internal Error"}},
        "PutObject",
    )

    # Create test file
    test_file = create_test_file()

    # Make upload request
    files = {"file": (test_file_name, test_file, "text/csv")}
    response = client.post("/upload-file", files=files)

    # Verify response
    assert response.status_code == 500
    assert "Error" in response.json()["detail"]


# -------------------------- Integration Tests --------------------------


@pytest.mark.integration
@patch("routes.upload_file.upload_file.token_table")
@patch("routes.upload_file.upload_file.s3_client")
async def test_upload_file_full_flow(mock_s3, mock_token_table):
    """Test complete file upload flow"""
    # Configure mocks
    mock_token_table.scan.return_value = {
        "Items": [
            {
                "token": valid_token,
                "expiration": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            }
        ]
    }
    mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    # Create test file with multiple lines
    test_content = f"{valid_token}\nline1\nline2\nline3"
    test_file = create_test_file(test_content)

    # Make upload request
    files = {"file": (test_file_name, test_file, "text/csv")}
    response = client.post("/upload-file", files=files)

    # Verify complete flow
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["file_name"] == test_file_name

    # Verify S3 upload was called with correct content
    mock_s3.put_object.assert_called_once()
    _, kwargs = mock_s3.put_object.call_args
    assert kwargs["Body"].decode() == "line1\nline2\nline3"


# -------------------------- Test Fixtures --------------------------


@pytest.fixture
def mock_s3_client():
    """Fixture for S3 client"""
    with patch("routes.upload_file.upload_file.s3_client") as mock_s3:
        mock_s3.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        yield mock_s3


@pytest.fixture
def mock_token_validator():
    """Fixture for token validation"""
    with patch("routes.upload_file.upload_file.verify_token") as mock_verify:
        mock_verify.return_value = True
        yield mock_verify
