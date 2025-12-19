"""
INGESTOR SERVICE - The Ear
Lắng nghe tin nhắn từ Telegram Channels/Groups và đẩy vào Redis Queue.
"""
import os
import asyncio
import json
import sys

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common.logger import get_logger
from src.common.redis_client import get_redis

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_NAME = 'sessions/ingestor_session'

logger = get_logger("ingestor")

# Queue name
QUEUE_RAW_MESSAGES = "queue:raw_messages"

# Create client
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


@client.on(events.NewMessage)
async def message_handler(event):
    """
    Xử lý mỗi tin nhắn mới từ bất kỳ chat nào.
    Chỉ serialize và đẩy vào Redis, KHÔNG xử lý logic.
    """
    try:
        # Bỏ qua tin nhắn từ chính mình
        if event.out:
            return
        
        # Bỏ qua tin nhắn private (chỉ lắng nghe groups/channels)
        if event.is_private:
            return
        
        # Bỏ qua nếu không có text
        if not event.text:
            return
        
        # Lấy thông tin chat
        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'Unknown')
        
        # Serialize message data
        message_data = {
            "id": event.id,
            "chat_id": event.chat_id,
            "chat_title": chat_title,
            "text": event.text,
            "date": event.date.isoformat(),
            "sender_id": event.sender_id,
            "message_link": f"https://t.me/c/{str(event.chat_id)[4:]}/{event.id}" if str(event.chat_id).startswith("-100") else None
        }
        
        # Push to Redis Queue
        redis = await get_redis()
        await redis.lpush(QUEUE_RAW_MESSAGES, json.dumps(message_data, ensure_ascii=False))
        
        logger.debug(f"Ingested: [{chat_title}] {event.text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def main():
    """Main entry point for Ingestor Service."""
    logger.info("=" * 50)
    logger.info("INGESTOR SERVICE - Starting...")
    logger.info("=" * 50)
    
    # Ensure sessions directory exists
    os.makedirs("sessions", exist_ok=True)
    
    try:
        # Connect to Telegram
        await client.start()
        
        me = await client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username})")
        
        # Get dialogs count
        dialogs = await client.get_dialogs(limit=0)
        logger.info(f"Listening to {dialogs.total} chats...")
        
        # Test Redis connection
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection: OK")
        
        logger.info("Ingestor is running. Waiting for messages...")
        
        # Run until disconnected
        await client.run_until_disconnected()
        
    except SessionPasswordNeededError:
        logger.error("2FA is enabled. Please run this script interactively first.")
    except Exception as e:
        logger.error(f"Ingestor error: {e}")
        raise


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Ingestor stopped by user.")
