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
        response = movements_table.scan(
            FilterExpression=Attr("UserId").eq(user_id)
            & Attr("Date").between(
                start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )
        )

        transactions = response["Items"]
        logger.info(f"📝 Found {len(transactions)} transactions")

        # Log transaction dates for verification
        for trans in transactions:
            logger.info(f"Transaction date: {trans['Date']}, amount: {trans['amount']}")

        return transactions

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
            "transaction_count": 0,  # Added for verification
        }

    total_balance = Decimal("0")
    transactions_by_month = {}
    debit_amounts = []
    credit_amounts = []

    for trans in transactions:
        amount = Decimal(str(trans["amount"]))
        total_balance += amount

        # Log each transaction for verification
        logger.info(f"Processing transaction: Date={trans['Date']}, Amount={amount}")

        date = datetime.strptime(trans["Date"], "%Y-%m-%d")
        month = date.strftime("%B")
        transactions_by_month[month] = transactions_by_month.get(month, 0) + 1

        if amount < 0:
            debit_amounts.append(amount)
        else:
            credit_amounts.append(amount)

    avg_debit = sum(debit_amounts) / len(debit_amounts) if debit_amounts else 0
    avg_credit = sum(credit_amounts) / len(credit_amounts) if credit_amounts else 0

    # Log summary calculations for verification
    logger.info(f"💰 Total balance calculated: {float(total_balance)}")
    logger.info(f"📈 Average credits: {float(avg_credit)}")
    logger.info(f"📉 Average debits: {float(avg_debit)}")
    logger.info(f"📅 Transactions by month: {transactions_by_month}")
    logger.info(f"🔢 Number of transactions: {len(transactions)}")

    return {
        "total_balance": float(total_balance),
        "transactions_by_month": dict(transactions_by_month),
        "avg_debit": float(avg_debit),
        "avg_credit": float(avg_credit),
        "transaction_count": len(transactions),  # Added for verification
        "date_range": {
            "start": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end": datetime.now().strftime("%Y-%m-%d"),
        },
    }


def send_summary_email(email: str, summary: dict):
    logger.info(f"📧 Preparing email for: {email}")
    subject = "Your Monthly Transaction Summary"

    # Read the logo image file and encode it
    try:
        with open("stori.jpeg", "rb") as f:
            logo_data = f.read()
            logo_base64 = base64.b64encode(logo_data).decode()
    except Exception as e:
        logger.error(f"💥 Error reading logo file: {str(e)}")
        logo_base64 = ""

    body_html = f"""
    <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333333;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    padding: 20px 0;
                    background-color: #f8f9fa;
                }}
                .logo {{
                    max-width: 150px;
                    height: auto;
                }}
                .summary-box {{
                    background-color: #ffffff;
                    border: 1px solid #e9ecef;
                    border-radius: 5px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .balance {{
                    font-size: 24px;
                    color: #2c3e50;
                    text-align: center;
                    padding: 15px 0;
                    margin: 10px 0;
                    background-color: #f8f9fa;
                    border-radius: 5px;
                }}
                .transactions-list {{
                    list-style: none;
                    padding: 0;
                }}
                .transaction-item {{
                    padding: 10px 0;
                    border-bottom: 1px solid #e9ecef;
                }}
                .averages {{
                    display: flex;
                    justify-content: space-between;
                    margin-top: 20px;
                }}
                .average-box {{
                    flex: 1;
                    text-align: center;
                    padding: 15px;
                    margin: 0 10px;
                    background-color: #f8f9fa;
                    border-radius: 5px;
                }}
                .debit {{
                    color: #dc3545;
                }}
                .credit {{
                    color: #28a745;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px 0;
                    font-size: 12px;
                    color: #6c757d;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="data:image/jpeg;base64,{logo_base64}" alt="Stori Logo" class="logo">
                    <h1>Transaction Summary</h1>
                    <p>Last 30 Days Activity</p>
                </div>
                
                <div class="summary-box">
                    <div class="balance">
                        <strong>Total Balance</strong>
                        <br>
                        ${summary['total_balance']:.2f}
                    </div>
                    
                    <h3>Transactions by Month</h3>
                    <ul class="transactions-list">
                        {" ".join([f'''
                        <li class="transaction-item">
                            <strong>{month}:</strong> {count} transactions
                        </li>
                        ''' for month, count in summary['transactions_by_month'].items()])}
                    </ul>
                    
                    <div class="averages">
                        <div class="average-box">
                            <h4>Average Debits</h4>
                            <span class="debit">${abs(summary['avg_debit']):.2f}</span>
                        </div>
                        <div class="average-box">
                            <h4>Average Credits</h4>
                            <span class="credit">${summary['avg_credit']:.2f}</span>
                        </div>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated message from Stori. Please do not reply to this email.</p>
                    <p>If you have any questions, please contact our support team.</p>
                </div>
            </div>
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
