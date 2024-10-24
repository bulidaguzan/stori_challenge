from fastapi import APIRouter

router = APIRouter()
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# -------------------------- HEALTCHECK  --------------------------
@router.get("/health", tags=["HealthCheck"])
async def health_check():
    return {"status": "healthy"}
