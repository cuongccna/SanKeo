from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from src.common.logger import get_logger
# from src.database.db import get_db # Import DB logic to update user
# from src.database.models import Transaction, User

app = FastAPI()
logger = get_logger("payment")

class SePayWebhook(BaseModel):
    id: str
    amount: float
    content: str
    # Add other fields as per SePay documentation

@app.post("/webhook/sepay")
async def sepay_webhook(data: SePayWebhook):
    logger.info(f"Received payment: {data}")
    
    # 1. Parse content to find User ID
    # 2. Update Transaction table
    # 3. Update User expiry_date
    # 4. Notify User via Bot (could push to a queue or call bot API directly)
    
    return {"status": "success"}

# To run: uvicorn src.bot.payment_server:app --host 0.0.0.0 --port 8000
