from fastapi import HTTPException, APIRouter
from models import UserCreate
from passlib.apps import custom_app_context as pwd_context
from fastapi.responses import JSONResponse
from dynamo import create_user, get_user_by_email

from fastapi import APIRouter

router = APIRouter()


# -------------------------- REGISTER  --------------------------
@router.post("/register", tags=["Users"])
async def register(user: UserCreate):
    print(f"Starting register new user...")
    try:
        print(f"Checking if user with email {user.email} already exists")
        existing_user = get_user_by_email(user.email)
        print(f"Checking user:{existing_user}")
        if existing_user:
            msg = "User already exist"
            print(msg)
            return {"message": msg}
        else:
            print("Hashing password...")
            hashed_password = pwd_context.hash(user.password)
            print("Saving into db...")
            user.password = hashed_password
            await create_user(user)
            return {
                "email": user.email,
                "password": "Save into database, and encrypt for your security.",
                "name": user.name,
            }

    except HTTPException as http_ex:
        print(f"HTTP Exception occurred: {http_ex.detail}")
        return JSONResponse(
            status_code=http_ex.status_code, content={"detail": http_ex.detail}
        )
    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
        return JSONResponse(
            status_code=500, content={"detail": "An unexpected error occurred"}
        )
