import uuid
import boto3
from datetime import datetime
from models import UserCreate, User
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("users")


def create_user(user: UserCreate, hashed_password: str):
    print("Creadno usuario")
    timestamp = datetime.utcnow().isoformat()
    user_dict = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "name": user.name,
        "password": hashed_password,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    try:
        table.put_item(
            Item=user_dict, ConditionExpression="attribute_not_exists(email)"
        )
        print("Guardado")

        return user
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError("Email already exists")
        raise
