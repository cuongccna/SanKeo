import os
import sys
import re
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from aiogram import Bot

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common.config import settings
from src.database.db import AsyncSessionLocal
from src.database.models import User, PlanType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook")

app = FastAPI()
bot = Bot(token=settings.BOT_TOKEN)

class SePayPayload(BaseModel):
    id: int
    gateway: str
    transactionDate: str
    accountNumber: str
    subAccount: Optional[str] = None
    amount: float
    content: str
    transferType: str
    transferAmount: float
    accumulated: float
    code: Optional[str] = None
    referenceCode: Optional[str] = None
    description: Optional[str] = None

async def notify_user(user_id: int, amount: float, new_expiry: datetime):
    """Send notification to user via Telegram."""
    try:
        expiry_str = new_expiry.strftime("%d/%m/%Y")
        message = (
            f"✅ **Thanh toán thành công!**\n\n"
            f"💰 Số tiền: {amount:,.0f} VND\n"
            f"💎 Gói: **VIP**\n"
            f"⏳ Hạn sử dụng: **{expiry_str}**\n\n"
            f"Cảm ơn bạn đã ủng hộ SanKeo Bot! 🚀"
        )
        await bot.send_message(user_id, message, parse_mode="Markdown")
        logger.info(f"Notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send notification to {user_id}: {e}")

@app.post("/sepay-webhook")
async def sepay_webhook(payload: SePayPayload, background_tasks: BackgroundTasks):
    logger.info(f"Received webhook: {payload}")

    # 1. Verify basic data (Optional: Check API Key if SePay sends it in headers)
    # For now, we trust the payload structure.

    # 2. Extract User ID from content
    # Pattern: "USER 12345" or "USER12345" (Case insensitive)
    match = re.search(r"USER\s*(\d+)", payload.content, re.IGNORECASE)
    
    if not match:
        logger.warning(f"No User ID found in content: {payload.content}")
        return {"status": "success", "message": "No User ID found, ignored"}
    
    user_id = int(match.group(1))
    logger.info(f"Processing payment for User ID: {user_id}")

    # 3. Update Database
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User {user_id} not found in DB")
            # Optional: Create user if not exists? 
            # For now, we assume user must interact with bot first.
            return {"status": "error", "message": "User not found"}

        # Calculate new expiry
        now = datetime.utcnow()
        days_to_add = 30 # Default 30 days
        
        # If user is already VIP and not expired, add to existing expiry
        if user.plan_type == PlanType.VIP and user.expiry_date and user.expiry_date > now:
            user.expiry_date += timedelta(days=days_to_add)
        else:
            # New VIP or expired
            user.expiry_date = now + timedelta(days=days_to_add)
        
        user.plan_type = PlanType.VIP
        
        # 4. Affiliate Commission
        if user.referrer_id:
            referrer_result = await session.execute(select(User).where(User.id == user.referrer_id))
            referrer = referrer_result.scalar_one_or_none()
            
            if referrer:
                commission_rate = 0.20 # 20%
                commission_amount = payload.amount * commission_rate
                
                # Update balance
                referrer.commission_balance = float(referrer.commission_balance or 0.0) + commission_amount
                
                # Notify referrer
                try:
                    msg = f"💰 **Hoa hồng Affiliate!**\n\nBạn nhận được **{commission_amount:,.0f} VND** từ thành viên tuyến dưới.\nSố dư hiện tại: {referrer.commission_balance:,.0f} VND"
                    await bot.send_message(referrer.id, msg, parse_mode="Markdown")
                    logger.info(f"Commission {commission_amount} added to referrer {referrer.id}")
                except Exception as e:
                    logger.error(f"Failed to notify referrer {referrer.id}: {e}")

        await session.commit()
        logger.info(f"User {user_id} upgraded to VIP until {user.expiry_date}")

        # 5. Notify User (Background task)
        background_tasks.add_task(notify_user, user_id, payload.amount, user.expiry_date)

    return {"status": "success", "user_id": user_id, "new_expiry": user.expiry_date}

@app.get("/")
async def root():
    return {"message": "SanKeo Payment Webhook is running"}
