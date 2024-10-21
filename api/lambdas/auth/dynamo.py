import uuid
import boto3
from datetime import datetime

from models import UserCreate, User, LoginRequest
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from passlib.apps import custom_app_context as pwd_context

# Configure dynamodb
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("users")


async def create_user(user: UserCreate):
    print("Creating user...")
    try:
        print("Saving user...")
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
        print("Save succesfull ")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError("Email already exists")
        raise


def get_user_by_email(email: str):
    try:
        # Use a scan because the index have cost. (not for production)
        print("Getting user... ")
        response = table.scan(FilterExpression=Attr("email").eq(email))
        # print(f"{response}")
        if response["Items"] != []:
            print("User found")
            return True
        else:
            print("User not found")
            return False
    except ClientError as e:
        logger.error(f"Error fetching user by email: {str(e)}")
        raise


def verify_user(login_request: LoginRequest):
    user = get_user_by_email(login_request.email)
    if user and pwd_context.verify(login_request.password, user["password"]):
        print("User exist and password correct")
        return user
    print("Error in user or password")
    return None
