from fastapi import APIRouter, UploadFile, File, HTTPException
import boto3
from botocore.exceptions import ClientError
import logging
from typing import Optional
from datetime import datetime
from boto3.dynamodb.conditions import Attr

router = APIRouter()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# S3 Configuration
s3_client = boto3.client("s3")
BUCKET_NAME = "stori-challenge-bucket"

# DynamoDB Configuration
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
token_table = dynamodb.Table("tokens")


def verify_token(token: str) -> bool:
    try:
        response = token_table.scan(FilterExpression=Attr("token").eq(token))

        if not response["Items"]:
            logger.info("Token not found in database")
            return False

        token_data = response["Items"][0]
        expiration = datetime.fromisoformat(token_data["expiration"])

        if expiration < datetime.utcnow():
            logger.info("Token has expired")
            return False

        return True

    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return False


@router.post("/upload-file", tags=["File Upload"])
async def upload_file(file: UploadFile = File(...), folder: Optional[str] = None):
    try:
        # Read the first line (token)
        content = await file.read()
        content_str = content.decode("utf-8")

        # Split content into lines
        lines = content_str.splitlines()
        if not lines:
            raise HTTPException(status_code=400, detail="File is empty")

        token = lines[0].strip()

        # Verify token
        if not verify_token(token):
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # Remove the token line and join the rest of the content
        file_content = "\n".join(lines[1:]).encode("utf-8")

        # Construct S3 path
        s3_path = file.filename
        if folder:
            s3_path = f"{folder}/{file.filename}"

        # Upload modified content to S3
        s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_path, Body=file_content)

        logger.info(
            f"File {file.filename} successfully uploaded to {BUCKET_NAME}/{s3_path}"
        )

        return {
            "status": "success",
            "message": "File uploaded successfully",
            "file_name": file.filename,
            "s3_path": s3_path,
        }

    except HTTPException as e:
        raise e
    except ClientError as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    finally:
        await file.close()
