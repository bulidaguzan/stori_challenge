import uuid
import boto3
from datetime import datetime

from .models import UserCreate, User, LoginRequest
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from passlib.apps import custom_app_context as pwd_context

# Configure dynamodb
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("users")
token_table = dynamodb.Table("tokens")
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


async def create_user(user: UserCreate):
    logger.info("🔐 Starting user creation process...")
    try:
        logger.info("💾 Attempting to save new user to database...")
        timestamp = datetime.utcnow().isoformat()
        user_dict = {
            "id": str(uuid.uuid4()),
            "email": user.email,
            "name": user.name,
            "password": user.password,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        table.put_item(
            Item=user_dict, ConditionExpression="attribute_not_exists(email)"
        )
        logger.info(f"✅ User successfully created with email: {user.email}")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning(f"⚠️ Registration failed: Email {user.email} already exists")
            raise ValueError("Email already exists")
        logger.error(f"❌ Database error during user creation: {str(e)}")
        raise


def get_user_by_email(email: str):
    try:
        logger.info(f"🔍 Searching for user with email: {email}")
        # Use a scan because the index have cost. (not for production)
        response = table.scan(FilterExpression=Attr("email").eq(email))
        logger.debug(f"📊 Database response: {response}")

        if response["Items"]:
            logger.info(f"✅ User found: {email}")
            return response["Items"][0]
        else:
            logger.warning(f"⚠️ No user found with email: {email}")
            return None

    except ClientError as e:
        logger.error(f"❌ Database error while fetching user: {str(e)}")
        raise


def verify_user(login_request: LoginRequest):
    logger.info(f"🔐 Attempting to verify user: {login_request.email}")
    user = get_user_by_email(login_request.email)

    if not user:
        logger.warning(
            f"⚠️ Authentication failed: User not found - {login_request.email}"
        )
        return None

    logger.debug("🔑 Verifying password hash...")
    if pwd_context.verify(login_request.password, user["password"]):
        logger.info(f"✅ User successfully authenticated: {login_request.email}")
        return user

    logger.warning(
        f"⚠️ Authentication failed: Invalid password for user {login_request.email}"
    )
    return None


def save_token(email: str, token: str, expiration: datetime):
    try:
        logger.info(f"🎟️ Saving authentication token for user: {email}")
        token_table.put_item(
            Item={
                "email": email,
                "token": token,
                "expiration": expiration.isoformat(),
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        logger.info(f"✅ Token successfully saved for user: {email}")
        logger.debug(f"📅 Token expiration set to: {expiration.isoformat()}")

    except Exception as e:
        logger.error(f"❌ Failed to save authentication token: {str(e)}")
        raise

