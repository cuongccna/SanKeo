"""
WORKER SERVICE - The Brain
Lấy tin từ Redis Queue, filter theo keywords, và đẩy notifications.
"""
import os
import sys
import asyncio
import json
import re
import hashlib
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common.logger import get_logger
from src.common.redis_client import get_redis
from src.database.db import AsyncSessionLocal
from src.database.models import FilterRule as DBFilterRule, User, PlanType
from src.worker.filter_engine import MessageProcessor, FilterRule as EngineFilterRule
from src.worker.ai_engine import ai_engine

logger = get_logger("worker")

# Queue names
QUEUE_RAW_MESSAGES = "queue:raw_messages"
QUEUE_NOTIFICATIONS = "queue:notifications"

# Free user limits
FREE_MAX_KEYWORDS = 3
FREE_MAX_NOTIFICATIONS_PER_DAY = 10

# Initialize Processor
processor = MessageProcessor()


async def check_user_can_receive(redis, user: User) -> bool:
    """
    Check if user can receive notification (VIP or within free limits).
    Also checks Quiet Mode.
    """
    # 1. Check Quiet Mode
    if user.quiet_start and user.quiet_end:
        now = datetime.utcnow().time()
        start = user.quiet_start
        end = user.quiet_end
        
        is_quiet = False
        if start < end:
            # Example: 23:00 to 23:59 (Same day range? No, usually overnight)
            # If start < end (e.g. 13:00 to 14:00), then quiet if now in between
            if start <= now <= end:
                is_quiet = True
        else:
            # Example: 23:00 to 07:00 (Overnight)
            # Quiet if now >= 23:00 OR now <= 07:00
            if now >= start or now <= end:
                is_quiet = True
        
        if is_quiet:
            # logger.debug(f"User {user.id} is in Quiet Mode ({start} - {end})")
            return False

    # VIP users: always can receive (if not in quiet mode)
    if user.plan_type == PlanType.VIP:
        if user.expiry_date and user.expiry_date > datetime.utcnow():
            return True
        # VIP expired, treat as FREE
    
    # FREE users: check daily limit
    today = datetime.utcnow().strftime("%Y-%m-%d")
    counter_key = f"notif_count:{user.id}:{today}"
    
    count = await redis.get(counter_key)
    count = int(count) if count else 0
    
    if count >= FREE_MAX_NOTIFICATIONS_PER_DAY:
        return False
    
    # Increment counter
    await redis.incr(counter_key)
    await redis.expire(counter_key, 86400)  # Expire after 24h
    
    return True


async def process_message(redis, message_data: dict):
    """
    Process a single message using Filter Engine.
    """
    async with AsyncSessionLocal() as session:
        # Fetch active rules with user info
        result = await session.execute(
            select(DBFilterRule)
            .options(selectinload(DBFilterRule.user))
            .where(DBFilterRule.is_active == True)
        )
        db_rules = result.scalars().all()
        
        # Convert DB rules to Engine rules
        engine_rules = []
        rule_map = {} # Map engine rule ID back to DB rule object to get user info
        
        for db_rule in db_rules:
            # Simple conversion: keyword -> must_have
            # TODO: In future, DB should support must_not_have columns
            e_rule = EngineFilterRule(
                id=db_rule.id,
                user_id=db_rule.user_id,
                must_have=[db_rule.keyword], 
                must_not_have=[]
            )
            engine_rules.append(e_rule)
            rule_map[db_rule.id] = db_rule

        # 1. First Pass: Filter on Caption (Text only)
        # This saves OCR costs if the caption already matches or is clearly spam.
        matched_rules = processor.process_incoming_message(message_data, engine_rules)

        # 2. Second Pass: OCR (Only if no match found AND image exists)
        image_path = message_data.get("image_path")
        # Check if image scanning is disabled
        inactive_img = os.getenv("INACTIVE_IMG", "False").lower() in ("true", "1", "yes")

        if not matched_rules and image_path and os.path.exists(image_path) and not inactive_img:
            logger.info(f"No text match found. Attempting OCR on: {image_path}")
            try:
                ocr_text = await ai_engine.extract_text_from_image(image_path)
                if ocr_text:
                    logger.info(f"OCR Result: {ocr_text[:50]}...")
                    # Append OCR text to message text
                    message_data['text'] += f"\n\n[OCR Content]:\n{ocr_text}"
                    
                    # Run Filter again with enriched text
                    matched_rules = processor.process_incoming_message(message_data, engine_rules)
            except Exception as e:
                logger.error(f"Error during OCR processing: {e}")
        
        # Cleanup Image (Always delete if it exists)
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                logger.info(f"Deleted temp image: {image_path}")
            except Exception as e:
                logger.error(f"Failed to delete temp image {image_path}: {e}")

        
        if not matched_rules:
            return

        # AI Analysis (Lazy load: only if needed)
        ai_analysis_result = None

        # Track which users already matched (avoid duplicate notifications)
        notified_users = set()
        
        for match in matched_rules:
            db_rule = rule_map.get(match.id)
            if not db_rule:
                continue
                
            # Skip if user already notified for this message
            if db_rule.user_id in notified_users:
                continue
            
            # Check if user can receive
            if not await check_user_can_receive(redis, db_rule.user):
                logger.debug(f"User {db_rule.user_id} reached daily limit")
                continue
            
            # AI Analysis for VIP
            analysis_text = None
            # Check VIP status (assuming PlanType.VIP is defined and user object has it)
            # If user.plan_type is a string or enum, handle accordingly.
            # Based on models.py, PlanType is an Enum.
            if db_rule.user.plan_type == PlanType.VIP:
                if ai_analysis_result is None:
                     logger.info("Performing AI Analysis for VIP user...")
                     ai_analysis_result = await ai_engine.analyze_message(message_data.get('text', ''))
                analysis_text = ai_analysis_result

            # Create notification
            notification = {
                "user_id": db_rule.user_id,
                "message": message_data,
                "matched_keyword": db_rule.keyword,
                "timestamp": datetime.utcnow().isoformat(),
                "ai_analysis": analysis_text
            }
            
            await redis.lpush(QUEUE_NOTIFICATIONS, json.dumps(notification, ensure_ascii=False))
            notified_users.add(db_rule.user_id)
            
            logger.info(f"Match: user={db_rule.user_id}, keyword='{db_rule.keyword}', chat={message_data.get('chat_title', 'Unknown')}")



async def main():
    """Main entry point for Worker Service."""
    logger.info("=" * 50)
    logger.info("WORKER SERVICE - Starting...")
    logger.info("=" * 50)
    
    redis = await get_redis()
    
    # Test Redis connection
    await redis.ping()
    logger.info("Redis connection: OK")
    
    logger.info(f"Listening to queue: {QUEUE_RAW_MESSAGES}")
    logger.info("Worker is running. Waiting for messages...")
    
    while True:
        try:
            # Blocking pop from Redis (timeout 0 = wait forever)
            result = await redis.brpop(QUEUE_RAW_MESSAGES, timeout=0)
            
            if result:
                _, data = result
                message_data = json.loads(data)
                print(f"DEBUG: Worker received: {message_data.get('text', '')[:50]}")
                await process_message(redis, message_data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in queue: {e}")
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
