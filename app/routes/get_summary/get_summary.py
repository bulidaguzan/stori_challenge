from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
from decimal import Decimal
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import boto3.dynamodb.conditions as conditions
import logging

router = APIRouter()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Configuration
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
movements_table = dynamodb.Table("movements")
users_table = dynamodb.Table("users")
token_table = dynamodb.Table("tokens")
ses_client = boto3.client("ses", region_name="us-east-1")


# Define request model
class SummaryRequest(BaseModel):
    access_token: str


def verify_token(token: str) -> dict:
    try:
        logger.info("🔑 Verifying access token...")
        response = token_table.scan(FilterExpression=Attr("token").eq(token))

        if not response["Items"]:
            logger.warning("❌ Token not found in database")
            return None

        token_data = response["Items"][0]
        expiration = datetime.fromisoformat(token_data["expiration"])

        if expiration < datetime.utcnow():
            logger.warning("⏰ Token has expired")
            return None

        logger.info("✅ Token successfully verified")
        return token_data

    except Exception as e:
        logger.error(f"💥 Error while verifying token: {str(e)}")
        return None


def get_user_id_from_email(email: str) -> str:
    """
    Get UserId from account table using email
    """
    try:
        logger.info(f"🔍 Looking up UserId for email: {email}")
        response = users_table.scan(FilterExpression=Attr("email").eq(email))

        if not response["Items"]:
            logger.warning(f"❌ No account found for email: {email}")
            raise HTTPException(status_code=404, detail="Account not found")

        user_id = response["Items"][0]["id"]
        logger.info(f"✅ Found UserId: {user_id}")
        return user_id

    except Exception as e:
        logger.error(f"💥 Error retrieving UserId: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving user account")


def get_user_transactions(user_id: str) -> list:
    logger.info(f"📊 Retrieving transactions for user: {user_id}")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    try:
        logger.info(
            f"🗓️ Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )
        response = movements_table.scan(FilterExpression=Attr("UserId").eq(user_id))
        logger.info(f"📝 Found {len(response['Items'])} transactions")
        return response["Items"]
    except Exception as e:
        logger.error(f"💥 Error retrieving transactions: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving transactions")


def calculate_summary(transactions: list) -> dict:
    logger.info("🧮 Calculating transaction summary...")
    if not transactions:
        logger.info("ℹ️ No transactions to process")
        return {
            "total_balance": 0,
            "transactions_by_month": {},
            "avg_debit": 0,
            "avg_credit": 0,
        }

    total_balance = Decimal("0")
    transactions_by_month = {}
    debit_amounts = []
    credit_amounts = []

    for trans in transactions:
        amount = Decimal(str(trans["amount"]))
        total_balance += amount

        date = datetime.strptime(trans["Date"], "%Y-%m-%d")
        month = date.strftime("%B")
        transactions_by_month[month] = transactions_by_month.get(month, 0) + 1

        if amount < 0:
            debit_amounts.append(amount)
        else:
            credit_amounts.append(amount)

    avg_debit = sum(debit_amounts) / len(debit_amounts) if debit_amounts else 0
    avg_credit = sum(credit_amounts) / len(credit_amounts) if credit_amounts else 0

    logger.info(f"💰 Total balance calculated: {float(total_balance)}")
    logger.info(f"📈 Average credits: {float(avg_credit)}")
    logger.info(f"📉 Average debits: {float(avg_debit)}")

    return {
        "total_balance": float(total_balance),
        "transactions_by_month": dict(transactions_by_month),
        "avg_debit": float(avg_debit),
        "avg_credit": float(avg_credit),
    }


def send_summary_email(email: str, summary: dict):
    logger.info(f"📧 Preparing email for: {email}")
    subject = "Your Monthly Transaction Summary"
    body_html = f"""
    <html>
        <body>
            <h2>Transaction Summary for the Last 30 Days</h2>
            <p>Here's your financial summary:</p>
            <ul>
                <li>Total Balance: ${summary['total_balance']:.2f}</li>
                <li>Transactions by Month:
                    <ul>
                        {"".join([f"<li>{month}: {count}</li>" for month, count in summary['transactions_by_month'].items()])}
                    </ul>
                </li>
                <li>Average Debit Amount: ${summary['avg_debit']:.2f}</li>
                <li>Average Credit Amount: ${summary['avg_credit']:.2f}</li>
            </ul>
        </body>
    </html>
    """

    try:
        response = ses_client.send_email(
            Source="agustindaguzan@gmail.com",
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": body_html}},
            },
        )
        logger.info(f"✉️ Email sent successfully: {response['MessageId']}")
    except Exception as e:
        logger.error(f"💥 Error sending email: {str(e)}")
        raise HTTPException(status_code=500, detail="Error sending summary email")


@router.post("/get-summary", tags=["Transactions"])
async def get_summary(request: SummaryRequest):
    logger.info("🚀 Starting get-summary process")

    # Verify token from request body
    logger.info("🔒 Verifying authentication...")
    token_data = verify_token(request.access_token)
    if not token_data:
        logger.warning("🚫 Invalid or expired token")
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Get user email from token data
        user_email = token_data["email"]
        logger.info(f"👤 Processing request for user: {user_email}")

        # Get UserId from account table using email
        logger.info("🔍 Getting UserId from account...")
        user_id = get_user_id_from_email(user_email)

        # Get user's transactions using UserId
        logger.info("📊 Retrieving transactions...")
        transactions = get_user_transactions(user_id)

        # Calculate summary
        logger.info("📋 Generating summary...")
        summary = calculate_summary(transactions)

        # Send email
        logger.info("📤 Sending summary email...")
        send_summary_email(user_email, summary)

        logger.info("✨ Process completed successfully")
        return {
            "status": "success",
            "message": "Summary generated and sent successfully",
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"💥 Error processing summary request: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing summary request")
