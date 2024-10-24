from fastapi import HTTPException, APIRouter
from .models import UserCreate
from passlib.apps import custom_app_context as pwd_context
from fastapi.responses import JSONResponse
from .dynamo import create_user, get_user_by_email
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
router = APIRouter()


# -------------------------- REGISTER  --------------------------
@router.post("/register", tags=["Users"])
async def register(user: UserCreate):
    logger.info("🚀 Starting new user registration process...")
    try:
        logger.info(f"🔍 Checking if user exists: {user.email}")
        existing_user = get_user_by_email(user.email)

        if existing_user:
            logger.warning(f"❌ User already exists: {user.email}")
            return {"message": "User already exist"}

        logger.info("🔐 Hashing password...")
        hashed_password = pwd_context.hash(user.password)

        logger.info("💾 Saving user to database...")
        user.password = hashed_password
        user_dict = await create_user(user)

        logger.info("✅ User registration successful")
        return {
            "id": user_dict["id"],
            "email": user.email,
            "password": "Save into database, and encrypt for your security.",
            "name": user.name,
        }

    except HTTPException as http_ex:
        logger.error(f"🚫 HTTP Exception: {http_ex.detail}")
        return JSONResponse(
            status_code=http_ex.status_code, content={"detail": http_ex.detail}
        )
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=500, content={"detail": "An unexpected error occurred"}
        )
