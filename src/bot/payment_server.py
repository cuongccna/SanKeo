"""
PAYMENT GATEWAY - The Wallet
Xử lý webhook thanh toán từ SePay/Casso.
"""
import os
import sys
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Union
from decimal import Decimal

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy import select

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common.logger import get_logger
from src.common.redis_client import get_redis
from src.database.db import AsyncSessionLocal
from src.database.models import User, Transaction, PlanType

logger = get_logger("payment")

# ============ Config ============
VIP_PRICE = 50000.0  # 50.000 VND
BUSINESS_PRICE = 299000.0 # 299.000 VND
VIP_DURATION_DAYS = 30

# Daily Rates
VIP_DAILY_RATE = VIP_PRICE / 30
BUSINESS_DAILY_RATE = BUSINESS_PRICE / 30

# Queue for bot notifications
QUEUE_PAYMENT_NOTIFICATIONS = "queue:payment_notifications"


# ============ FastAPI App ============
app = FastAPI(
    title="SanKeo Payment Gateway",
    description="Webhook server for SePay/Casso payment processing",
    version="1.0.0"
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error(f"Validation Error: {exc.errors()}")
    logger.error(f"Request Body: {body.decode()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": body.decode()},
    )


# ============ Pydantic Models ============
class SePayWebhookData(BaseModel):
    """SePay webhook payload structure."""
    id: Union[str, int] = Field(..., description="Transaction ID from bank")
    gateway: Optional[str] = Field(default=None, description="Payment gateway name")
    transactionDate: Optional[str] = Field(default=None, description="Transaction date")
    accountNumber: Optional[str] = Field(default=None, description="Bank account number")
    code: Optional[str] = Field(default=None, description="Transaction code")
    content: str = Field(..., description="Transfer content/memo")
    transferType: str = Field(default="in", description="Transfer type: in/out")
    transferAmount: float = Field(..., description="Transfer amount")
    accumulated: float = Field(default=0, description="Accumulated balance")
    subAccount: Optional[str] = Field(default=None, description="Sub account")
    referenceCode: Optional[str] = Field(default=None, description="Reference code")
    description: Optional[str] = Field(default=None, description="Description")


class WebhookResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None


# ============ Helpers ============
def parse_user_id_from_content(content: str) -> Optional[int]:
    """
    Parse user ID from transfer content.
    Expected format: VIP 123456789 or VIP123456789
    """
    # Pattern: VIP followed by digits
    patterns = [
        r'VIP\s*(\d+)',      # VIP 123456789 or VIP123456789
        r'BUS\s*(\d+)',      # BUS 123456789 (Business)
        r'BUSINESS\s*(\d+)', # BUSINESS 123456789
        r'SANKEO\s*(\d+)',   # SANKEO 123456789
        r'AH\s*(\d+)',       # AH 123456789 (Alpha Hunter)
    ]
    
    content_upper = content.upper()
    
    for pattern in patterns:
        match = re.search(pattern, content_upper)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None


async def process_vip_upgrade(user_id: int, transaction_id: str, amount: float) -> bool:
    """
    Process VIP upgrade for a user.
    Returns True if successful.
    """
    async with AsyncSessionLocal() as session:
        # Check if transaction already processed
        existing_tx = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        if existing_tx.scalar_one_or_none():
            logger.warning(f"Transaction {transaction_id} already processed")
            return False
        
        # Get user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User {user_id} not found for payment")
            return False
        
        # Determine Plan and Rate
        # Logic:
        # 1. If amount >= BUSINESS_PRICE -> Upgrade/Extend BUSINESS
        # 2. If user is already BUSINESS -> Extend BUSINESS (even with small amount)
        # 3. Else -> VIP
        
        target_plan = PlanType.VIP
        daily_rate = VIP_DAILY_RATE
        
        if amount >= BUSINESS_PRICE:
            target_plan = PlanType.BUSINESS
            daily_rate = BUSINESS_DAILY_RATE
        elif user.plan_type == PlanType.BUSINESS:
            target_plan = PlanType.BUSINESS
            daily_rate = BUSINESS_DAILY_RATE
            
        # Calculate days to add
        days_to_add = amount / daily_rate
        
        # Calculate new expiry date
        now = datetime.utcnow()
        
        # Handle timezone awareness for comparison
        current_expiry = user.expiry_date
        if current_expiry:
            # If current_expiry is aware but now is naive, make now aware (UTC)
            if current_expiry.tzinfo is not None and now.tzinfo is None:
                from datetime import timezone
                now = now.replace(tzinfo=timezone.utc)
            # If current_expiry is naive but now is aware, make current_expiry aware
            elif current_expiry.tzinfo is None and now.tzinfo is not None:
                from datetime import timezone
                current_expiry = current_expiry.replace(tzinfo=timezone.utc)

        if current_expiry and current_expiry > now:
            # Extend from current expiry
            new_expiry = current_expiry + timedelta(days=days_to_add)
        else:
            # Start fresh
            new_expiry = now + timedelta(days=days_to_add)
        
        # Update user
        user.plan_type = target_plan
        user.expiry_date = new_expiry
        
        # Create transaction record
        transaction = Transaction(
            id=transaction_id,
            user_id=user_id,
            amount=Decimal(str(amount)),
            status="SUCCESS"
        )
        session.add(transaction)
        
        await session.commit()
        
        logger.info(f"Payment processed: user={user_id}, plan={target_plan}, days={days_to_add:.2f}, amount={amount}")
        return True


async def notify_user_payment(user_id: int, amount: float, expiry_date: datetime):
    """Push notification to queue for bot to send."""
    redis = await get_redis()
    
    notification = {
        "type": "payment_success",
        "user_id": user_id,
        "amount": amount,
        "expiry_date": expiry_date.isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await redis.lpush(QUEUE_PAYMENT_NOTIFICATIONS, json.dumps(notification))


# ============ Endpoints ============
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "SanKeo Payment Gateway"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    try:
        redis = await get_redis()
        await redis.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {e}"
    
    return {
        "status": "ok",
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/webhook/sepay", response_model=WebhookResponse)
async def sepay_webhook(data: SePayWebhookData):
    """
    Handle SePay webhook for incoming bank transfers.
    """
    logger.info(f"Received webhook: id={data.id}, amount={data.transferAmount}, content={data.content}")
    
    # Only process incoming transfers
    if data.transferType != "in":
        logger.debug(f"Skipping outgoing transfer: {data.id}")
        return WebhookResponse(success=True, message="Skipped outgoing transfer")
    
    # Parse user ID from content
    user_id = parse_user_id_from_content(data.content)
    
    if not user_id:
        logger.warning(f"Could not parse user ID from content: {data.content}")
        return WebhookResponse(success=False, message="Invalid transfer content format")
    
    # Check minimum amount (Allow small amounts, e.g. > 1000 VND to avoid spam)
    if data.transferAmount < 1000:
        logger.warning(f"Amount too low: {data.transferAmount}")
        return WebhookResponse(
            success=False, 
            message="Amount too low. Minimum: 1000 VND",
            user_id=user_id
        )
    
    # Process upgrade
    success = await process_vip_upgrade(user_id, str(data.id), data.transferAmount)
    
    if success:
        # Get updated user info for notification
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                await notify_user_payment(user_id, data.transferAmount, user.expiry_date)
        
        return WebhookResponse(
            success=True,
            message="VIP upgraded successfully",
            user_id=user_id
        )
    else:
        return WebhookResponse(
            success=False,
            message="Failed to process upgrade",
            user_id=user_id
        )


@app.post("/webhook/casso")
async def casso_webhook(request: Request):
    """
    Handle Casso webhook (alternative to SePay).
    Casso has different payload structure.
    """
    try:
        body = await request.json()
        logger.info(f"Received Casso webhook: {body}")
        
        # Casso sends array of transactions
        transactions = body.get("data", [])
        
        for tx in transactions:
            # Map Casso fields to our format
            data = SePayWebhookData(
                id=str(tx.get("id", "")),
                content=tx.get("description", ""),
                transferAmount=float(tx.get("amount", 0)),
                transferType="in" if tx.get("amount", 0) > 0 else "out"
            )
            
            # Reuse SePay logic
            if data.transferType == "in":
                user_id = parse_user_id_from_content(data.content)
                if user_id and data.transferAmount >= 1000:
                    success = await process_vip_upgrade(user_id, data.id, data.transferAmount)
                    if success:
                        # Get updated user info for notification
                        async with AsyncSessionLocal() as session:
                            result = await session.execute(select(User).where(User.id == user_id))
                            user = result.scalar_one_or_none()
                            if user:
                                await notify_user_payment(user_id, data.transferAmount, user.expiry_date)
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Casso webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============ Run ============
# To run: uvicorn src.bot.payment_server:app --host 0.0.0.0 --port 8000
