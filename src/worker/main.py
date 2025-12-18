import asyncio
import json
import re
from sqlalchemy import select
from src.common.logger import get_logger
from src.common.redis_client import get_redis
from src.database.db import get_db
from src.database.models import FilterRule, User

logger = get_logger("worker")

async def process_message(redis, message_data):
    text = message_data.get("text", "")
    if not text:
        return

    # Deduplication (Simple check based on message content hash or ID)
    # For now, we skip complex deduplication logic
    
    # Fetch active rules
    async for session in get_db():
        result = await session.execute(select(FilterRule).where(FilterRule.is_active == True))
        rules = result.scalars().all()
        
        for rule in rules:
            if re.search(rule.keyword, text, re.IGNORECASE):
                notification = {
                    "user_id": rule.user_id,
                    "message": message_data,
                    "matched_keyword": rule.keyword
                }
                await redis.lpush("queue:notifications", json.dumps(notification))
                logger.info(f"Match found for user {rule.user_id}: {rule.keyword}")

async def main():
    logger.info("Starting Worker Service...")
    redis = await get_redis()
    
    while True:
        try:
            # Blocking pop from Redis
            _, data = await redis.brpop("queue:raw_messages")
            message_data = json.loads(data)
            await process_message(redis, message_data)
            
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
