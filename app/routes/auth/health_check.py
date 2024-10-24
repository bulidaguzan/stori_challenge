from fastapi import APIRouter

router = APIRouter()

# -------------------------- HEALTCHECK  --------------------------
@router.get("/health", tags=["HealthCheck"])
async def health_check():
    # print("Health check endpoint called")
    return {"status": "healthy"}
