from fastapi import HTTPException, APIRouter
from models import LoginRequest
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt
from dynamo import verify_user, save_token


from fastapi import APIRouter

router = APIRouter()


# -------------------------- Login  --------------------------
# Configuration
SECRET_KEY = "eyJLbGciOiJIUzI1NiIsInR5cCI6MkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQ8sw5m"  # Only for dev, hidden for prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict):
    print("Creating access token...")
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    print(f"Token expire: {expire}")
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print("Token create successfully")
    return encoded_jwt, expire


@router.post("/login", tags=["Users"])
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
