import uuid
import boto3
from datetime import datetime
from models import UserCreate, User
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("users")


def create_user(user: UserCreate):

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


def get_user(email: str):
    # Use a scan because the index have cost. (not for production)
    response = table.scan(FilterExpression=Attr("email").eq(email))
    print(response)

    if "Item" in response:
        return True
    else:
        return False
