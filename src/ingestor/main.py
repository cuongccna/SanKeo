import os
import asyncio
import json
from telethon import TelegramClient, events
from dotenv import load_dotenv
from src.common.logger import get_logger
from src.common.redis_client import get_redis

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = 'ingestor_session'

logger = get_logger("ingestor")

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage)
async def handler(event):
    try:
        redis = await get_redis()
        message_data = {
            "id": event.id,
            "chat_id": event.chat_id,
            "text": event.text,
            "date": event.date.isoformat(),
            "sender_id": event.sender_id
        }
        
        # Serialize and push to Redis
        await redis.lpush("queue:raw_messages", json.dumps(message_data))
        logger.debug(f"Ingested message from {event.chat_id}")
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")

async def main():
    logger.info("Starting Ingestor Service...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
