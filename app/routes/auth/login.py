from fastapi import HTTPException, APIRouter
from fastapi.responses import JSONResponse

from .models import LoginRequest
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt
from .dynamo import verify_user, save_token
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
from fastapi import APIRouter

router = APIRouter()

# Configuration
SECRET_KEY = "eyJLbGciOiJIUzI1NiIsInR5cCI6MkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQ8sw5m"  # Only for dev, hidden for prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict):
    logger.info("🔑 Starting access token creation...")
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    logger.info(f"⏰ Token expiration set to: {expire}")
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info("✅ Token created successfully")
    return encoded_jwt, expire


@router.post("/login", tags=["Users"])
async def login(login_request: LoginRequest):
    logger.info("🚀 Initiating login process...")
    try:
        logger.info("🔍 Verifying user credentials...")
        user = verify_user(login_request)
        if user == None:
            logger.warning("❌ Authentication failed: Invalid credentials")
            return JSONResponse(
                status_code=401, content={"detail": "Incorrect email or password"}
            )

        logger.info("👤 User authentication successful")
        logger.info("🔐 Generating access token...")
        access_token, expire = create_access_token(data={"sub": user["email"]})
        save_token(user["email"], access_token, expire)
        logger.info("✨ Login process completed successfully")
        return {"access_token": str(access_token), "token_type": "bearer"}

    except HTTPException as http_ex:
        logger.error(f"🚫 Login failed: {http_ex.detail}")
        raise http_ex  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"💥 Login process failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
