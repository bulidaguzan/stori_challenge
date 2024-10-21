from fastapi import FastAPI, HTTPException, Depends
from mangum import Mangum
from models import UserCreate, User, LoginRequest
from passlib.apps import custom_app_context as pwd_context
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt
from dynamo import create_user, get_user_by_email, verify_user, save_token

app = FastAPI(
    title="Stori - Auth",
)
handler = Mangum(app)
# Configuration
SECRET_KEY = "eyJLbGciOiJIUzI1NiIsInR5cCI6MkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQ8sw5m"  # Only for dev, hidden for prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# -------------------------- HEALTCHECK  --------------------------
@app.get("/health", tags=["HealthCheck"])
async def health_check():
    # print("Health check endpoint called")
    return {"status": "healthy"}


# -------------------------- REGISTER  --------------------------


@app.post("/register", tags=["Users"])
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


# -------------------------- Login  --------------------------


def create_access_token(data: dict):
    print("Creating access token...")
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    print(f"Token expire: {expire}")
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print("Token create successfully")
    return encoded_jwt, expire


@app.post("/login", tags=["Users"])
async def login(login_request: LoginRequest):
    print("Starting login...")
    try:
        print("Checking user and password...")
        user = verify_user(login_request)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        print("Creating access token...")
        access_token, expire = create_access_token(data={"sub": user["email"]})
        save_token(user["email"], access_token, expire)
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
