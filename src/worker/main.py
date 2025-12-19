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
from src.database.models import FilterRule, User, PlanType

logger = get_logger("worker")

# Queue names
QUEUE_RAW_MESSAGES = "queue:raw_messages"
QUEUE_NOTIFICATIONS = "queue:notifications"

# Deduplication settings
DEDUP_EXPIRE_SECONDS = 300  # 5 minutes
DEDUP_PREFIX = "dedup:"

# Free user limits
FREE_MAX_KEYWORDS = 3
FREE_MAX_NOTIFICATIONS_PER_DAY = 10


async def is_duplicate(redis, message_data: dict) -> bool:
    """
    Check if message is duplicate using Redis cache.
    Hash based on chat_id + message_id.
    """
    unique_key = f"{message_data['chat_id']}:{message_data['id']}"
    hash_key = hashlib.md5(unique_key.encode()).hexdigest()
    cache_key = f"{DEDUP_PREFIX}{hash_key}"
    
    # Check if exists
    exists = await redis.exists(cache_key)
    if exists:
        return True
    
    # Set with expiration
    await redis.setex(cache_key, DEDUP_EXPIRE_SECONDS, "1")
    return False


async def check_user_can_receive(redis, user: User) -> bool:
    """
    Check if user can receive notification (VIP or within free limits).
    """
    # VIP users: always can receive
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
    Process a single message: check rules and create notifications.
    """
    text = message_data.get("text", "")
    if not text:
        return
    
    # Deduplication check
    if await is_duplicate(redis, message_data):
        logger.debug(f"Duplicate message skipped: {message_data['id']}")
        return
    
    async with AsyncSessionLocal() as session:
        # Fetch active rules with user info
        result = await session.execute(
            select(FilterRule)
            .options(selectinload(FilterRule.user))
            .where(FilterRule.is_active == True)
        )
        rules = result.scalars().all()
        
        # Track which users already matched (avoid duplicate notifications)
        notified_users = set()
        
        for rule in rules:
            # Skip if user already notified for this message
            if rule.user_id in notified_users:
                continue
            
            # Regex matching
            try:
                if re.search(rule.keyword, text, re.IGNORECASE):
                    # Check if user can receive
                    if not await check_user_can_receive(redis, rule.user):
                        logger.debug(f"User {rule.user_id} reached daily limit")
                        continue
                    
                    # Create notification
                    notification = {
                        "user_id": rule.user_id,
                        "message": message_data,
                        "matched_keyword": rule.keyword,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await redis.lpush(QUEUE_NOTIFICATIONS, json.dumps(notification, ensure_ascii=False))
                    notified_users.add(rule.user_id)
                    
                    logger.info(f"Match: user={rule.user_id}, keyword='{rule.keyword}', chat={message_data.get('chat_title', 'Unknown')}")
                    
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{rule.keyword}': {e}")


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
