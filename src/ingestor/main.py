"""
INGESTOR SERVICE - The Ear
Lắng nghe tin nhắn từ Telegram Channels/Groups và đẩy vào Redis Queue.
With Smart Protection: Rate limiting, Flood detection, Account health monitoring.
"""
import os
import asyncio
import json
import sys

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest
from dotenv import load_dotenv
from datetime import datetime, timezone
from sqlalchemy import select

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common.logger import get_logger
from src.common.redis_client import get_redis
from src.common.utils import safe_execution
from src.database.db import AsyncSessionLocal
from src.database.models import BlacklistedChannel, SourceConfig
from src.ingestor.protection import (
    RateLimiter, FloodWaitHandler, BehaviorRandomizer, AccountHealthMonitor
)

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
# Use dedicated ingestor session for Telethon
SESSION_NAME = 'sessions/ingestor_telethon'  # Telethon format session
SESSION_PHONE = "ingestor_telethon"  # For protection module

# Get Bot ID to prevent self-loop
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_ID = int(BOT_TOKEN.split(":")[0]) if ":" in BOT_TOKEN else 0

logger = get_logger("ingestor")

# Queue name
QUEUE_RAW_MESSAGES = "queue:raw_messages"

# Protection modules
rate_limiter: RateLimiter = None
flood_handler: FloodWaitHandler = None
health_monitor: AccountHealthMonitor = None


# Rate Limiting
MAX_JOINS_PER_DAY = 20

# Blacklist cache
BLACKLISTED_CHANNELS = set()

# Source Config Cache
SOURCE_CONFIGS = {} # {chat_id: {"tag": "...", "priority": 1}}

# Create client
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def load_source_configs():
    """Load source configs from DB."""
    global SOURCE_CONFIGS
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SourceConfig))
            configs = result.scalars().all()
            SOURCE_CONFIGS = {
                cfg.chat_id: {"tags": cfg.tags, "priority": cfg.priority} 
                for cfg in configs
            }
            logger.info(f"Loaded {len(SOURCE_CONFIGS)} source configs.")
    except Exception as e:
        logger.error(f"Failed to load source configs: {e}")

async def health_check_loop():
    """
    Periodically check account health.
    Runs every 6 hours to detect issues early.
    """
    while True:
        await asyncio.sleep(6 * 3600)  # Every 6 hours
        
        if health_monitor:
            logger.info("🏥 Running periodic health check...")
            health = await health_monitor.check_health()
            
            if health["status"] == "danger":
                logger.critical("❌ DANGER: Account health is critical!")
                logger.critical(f"Issues: {health['issues']}")
            elif health["status"] == "warning":
                logger.warning(f"⚠️ Account health warning: {health['issues']}")

async def load_blacklist():
    """Load blacklisted channels from DB."""
    global BLACKLISTED_CHANNELS
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(BlacklistedChannel.channel_id))
            BLACKLISTED_CHANNELS = set(result.scalars().all())
            logger.info(f"Loaded {len(BLACKLISTED_CHANNELS)} blacklisted channels.")
    except Exception as e:
        logger.error(f"Failed to load blacklist: {e}")

async def refresh_config_loop():
    """Periodically refresh configurations."""
    while True:
        await asyncio.sleep(300)  # Refresh every 5 minutes
        logger.info("Refreshing configurations...")
        await load_blacklist()
        await load_source_configs()

async def join_channel(link: str):
    """
    Join a channel/group with Rate Limiting and FloodWait protection.
    """
    redis = await get_redis()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"daily_joins:{today}"
    
    # Check Rate Limit
    current_joins = await redis.get(key)
    current_joins = int(current_joins) if current_joins else 0
    
    if current_joins >= MAX_JOINS_PER_DAY:
        logger.warning(f"Rate Limit Reached: Cannot join {link}. Max {MAX_JOINS_PER_DAY} joins/day.")
        return

    try:
        logger.info(f"Attempting to join: {link}")
        # Use safe_execution to handle FloodWait automatically
        await safe_execution(client, JoinChannelRequest(link))
        
        # Update Counter
        await redis.incr(key)
        await redis.expire(key, 86400) # 24h TTL
        logger.info(f"Successfully joined {link}. Daily joins: {current_joins + 1}/{MAX_JOINS_PER_DAY}")
        
    except Exception as e:
        logger.error(f"Failed to join {link}: {e}")

@client.on(events.NewMessage)
async def message_handler(event):
    """
    Xử lý mỗi tin nhắn mới từ bất kỳ chat nào.
    WITH PROTECTION: Rate limiting, delay simulation, flood detection.
    """
    # ============ PROTECTION: Rate Limiting ============
    if not await rate_limiter.check_message_rate():
        logger.warning("Skipping message due to rate limit")
        return
    
    # ============ PROTECTION: Add Human-like Delay ============
    delay = await rate_limiter.get_message_delay()
    logger.debug(f"⏳ Waiting {delay:.1f}s before processing message...")
    await asyncio.sleep(delay)
    
    # Record this message
    await rate_limiter.record_message()
    
    # DEBUG: Print everything
    chat_title = "Unknown"
    try:
        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'Unknown')
    except:
        pass
    
    print(f"DEBUG: Received message: {event.text[:50] if event.text else 'Media'} from {event.chat_id} ({chat_title})")
    logger.debug(f"Ingested: [{chat_title}] {event.text[:50] if event.text else 'Media'}...")

    try:
        # Check blacklist
        if event.chat_id in BLACKLISTED_CHANNELS:
            logger.debug(f"Ignored message from blacklisted channel: {event.chat_id}")
            return

        # Prevent Infinite Loop: Ignore messages from the Bot itself
        if event.sender_id == BOT_ID:
            logger.debug(f"Ignored message from Bot ({BOT_ID}) to prevent loop.")
            return

        # Bỏ qua tin nhắn từ chính mình (Ingestor account)
        if event.out:
            return
        
        # Bỏ qua tin nhắn private (chỉ lắng nghe groups/channels)
        if event.is_private:
            return
        
        # Check for media (Photo)
        image_path = None
        # Check if image scanning is disabled
        inactive_img = os.getenv("INACTIVE_IMG", "False").lower() in ("true", "1", "yes")
        
        if event.photo and not inactive_img:
            try:
                # Create temp directory
                temp_dir = os.path.join(os.getcwd(), "temp_images")
                os.makedirs(temp_dir, exist_ok=True)
                
                # Download photo
                file_path = os.path.join(temp_dir, f"{event.chat_id}_{event.id}.jpg")
                await event.download_media(file=file_path)
                image_path = file_path
                logger.debug(f"Downloaded photo: {image_path}")
            except Exception as e:
                logger.error(f"Failed to download photo: {e}")

        # Bỏ qua nếu không có text VÀ không có ảnh
        if not event.text and not image_path:
            return
        
        # Lấy thông tin chat
        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'Unknown')
        
        # Tagging Logic
        source_config = SOURCE_CONFIGS.get(event.chat_id)
        tags = ["NORMAL"]
        priority = 1
        if source_config:
            tags = source_config.get("tags", ["NORMAL"])
            # Ensure tags is a list
            if not isinstance(tags, list):
                tags = [tags] if tags else ["NORMAL"]
                
            priority = source_config.get("priority", 1)
            logger.debug(f"Tagged message from {event.chat_id} as {tags} (Priority: {priority})")

        # Serialize message data
        message_data = {
            "id": event.id,
            "chat_id": event.chat_id,
            "chat_title": chat_title,
            "text": event.text or "",  # Ensure text is not None
            "date": event.date.isoformat(),
            "sender_id": event.sender_id,
            "message_link": f"https://t.me/c/{str(event.chat_id)[4:]}/{event.id}" if str(event.chat_id).startswith("-100") else None,
            "image_path": image_path,
            "tags": tags,
            "priority": priority
        }
        
        # Push to Redis Queue
        redis = await get_redis()
        await redis.lpush(QUEUE_RAW_MESSAGES, json.dumps(message_data, ensure_ascii=False))
        
        logger.debug(f"Ingested: [{chat_title}] {event.text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def main():
    """Main entry point for Ingestor Service."""
    global rate_limiter, flood_handler, health_monitor
    
    await load_blacklist()
    await load_source_configs()
    logger.info("=" * 50)
    logger.info("INGESTOR SERVICE - Starting with Account Protection...")
    logger.info("=" * 50)
    
    # ============ PROTECTION: Initialize Modules ============
    rate_limiter = RateLimiter(SESSION_PHONE)
    flood_handler = FloodWaitHandler(SESSION_PHONE)
    health_monitor = AccountHealthMonitor(client, SESSION_PHONE)
    
    await rate_limiter.init()
    logger.info(f"✅ Rate Limiter initialized (warm-up mode)")
    
    # Ensure sessions directory exists
    os.makedirs("sessions", exist_ok=True)
    
    try:
        # Connect to Telegram
        await client.start()
        
        me = await client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username})")
        
        # ============ PROTECTION: Check Account Health ============
        logger.info("🏥 Checking account health...")
        health = await health_monitor.check_health()
        if health["status"] == "danger":
            logger.critical("❌ Account health is CRITICAL! Aborting start.")
            return
        
        # Get dialogs count
        dialogs = await client.get_dialogs(limit=0)
        logger.info(f"Listening to {dialogs.total} chats...")
        
        # Test Redis connection
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection: OK")
        
        # ============ PROTECTION: Start Health Check Loop ============
        asyncio.create_task(health_check_loop())
        
        # Start config refresh loop
        asyncio.create_task(refresh_config_loop())
        
        logger.info("🛡️ Ingestor is running with smart protection. Waiting for messages...")
        
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
