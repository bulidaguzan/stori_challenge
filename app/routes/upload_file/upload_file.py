from fastapi import APIRouter, UploadFile, File, HTTPException
import boto3
from botocore.exceptions import ClientError
import logging
from typing import Optional
import os

router = APIRouter()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuración de S3
s3_client = boto3.client("s3")

BUCKET_NAME = "stori-challenge-bucket"


@router.post("/upload-file", tags=["File Upload"])
async def upload_file(file: UploadFile = File(...), folder: Optional[str] = None):
    try:
        # Construir la ruta del archivo en S3
        s3_path = file.filename
        if folder:
            s3_path = f"{folder}/{file.filename}"

        # Leer el contenido del archivo
        file_content = await file.read()

        # Subir el archivo a S3
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

    except ClientError as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

    finally:
        await file.close()
