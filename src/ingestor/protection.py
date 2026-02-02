"""
Account Protection Module - Prevent Telegram Ban/Lock
Implements intelligent rate limiting, flood detection, and human-like behavior.
"""
import asyncio
import random
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from telethon.errors import FloodWaitError, AuthKeyUnregisteredError, UnauthorizedError

from src.common.logger import get_logger
from src.common.redis_client import get_redis

logger = get_logger("protection")

# ============ CONFIG ============
# Warm-up: Gradually increase activity
WARM_UP_DAYS = 7
WARM_UP_SCHEDULE = {
    0: {"max_messages_per_hour": 10, "max_joins_per_day": 2},     # Day 1: Very conservative
    1: {"max_messages_per_hour": 15, "max_joins_per_day": 3},     # Day 2
    2: {"max_messages_per_hour": 20, "max_joins_per_day": 5},     # Day 3
    3: {"max_messages_per_hour": 30, "max_joins_per_day": 8},     # Day 4
    4: {"max_messages_per_hour": 40, "max_joins_per_day": 10},    # Day 5
    5: {"max_messages_per_hour": 50, "max_joins_per_day": 15},    # Day 6
    6: {"max_messages_per_hour": 60, "max_joins_per_day": 20},    # Day 7+: Normal
}

# Message Processing Delays
MIN_MESSAGE_DELAY = 5  # seconds
MAX_MESSAGE_DELAY = 15  # seconds
PAUSE_INTERVAL = 3600  # Pause every 1 hour
PAUSE_DURATION = (120, 300)  # 2-5 minutes pause

# Flood Detection
FLOOD_BACKOFF_MULTIPLIER = 1.5
FLOOD_MAX_BACKOFF = 600  # 10 minutes

# Health Check
HEALTH_CHECK_INTERVAL = 6 * 3600  # Every 6 hours


class RateLimiter:
    """Intelligent rate limiting based on account age and warm-up schedule."""
    
    def __init__(self, session_name: str):
        self.session_name = session_name
        self.session_key = f"session_info:{session_name}"
        self.last_message_time = {}
        
    async def init(self):
        """Initialize or load session info from Redis."""
        redis = await get_redis()
        session_info = await redis.get(self.session_key)
        
        if session_info:
            self.info = json.loads(session_info)
            logger.info(f"Loaded session info: created_at={self.info['created_at']}")
        else:
            # First time - initialize
            self.info = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "account_age_days": 0,
                "status": "warming_up",
                "flood_count": 0,
                "last_flood_time": None
            }
            await self.save()
            logger.info("New session initialized")
    
    async def save(self):
        """Save session info to Redis."""
        redis = await get_redis()
        await redis.set(self.session_key, json.dumps(self.info), ex=86400*30)  # 30 days
    
    async def get_account_age(self) -> int:
        """Get account age in days."""
        created = datetime.fromisoformat(self.info["created_at"])
        now = datetime.now(timezone.utc)
        return (now - created).days
    
    async def get_limits(self) -> Dict:
        """Get current rate limits based on warm-up schedule."""
        age_days = await self.get_account_age()
        schedule_day = min(age_days, WARM_UP_DAYS - 1)
        return WARM_UP_SCHEDULE[schedule_day]
    
    async def check_message_rate(self) -> bool:
        """
        Check if we can process another message.
        Returns True if OK, False if rate limit reached.
        """
        redis = await get_redis()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        hour = datetime.now(timezone.utc).hour
        hour_key = f"messages:{self.session_name}:{today}:{hour}"
        
        limits = await self.get_limits()
        current_count = await redis.get(hour_key)
        current_count = int(current_count) if current_count else 0
        
        if current_count >= limits["max_messages_per_hour"]:
            logger.warning(
                f"⚠️ Message rate limit reached: {current_count}/"
                f"{limits['max_messages_per_hour']} per hour"
            )
            return False
        
        return True
    
    async def record_message(self):
        """Record message processing."""
        redis = await get_redis()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        hour = datetime.now(timezone.utc).hour
        hour_key = f"messages:{self.session_name}:{today}:{hour}"
        
        await redis.incr(hour_key)
        await redis.expire(hour_key, 3600)
    
    async def get_message_delay(self) -> float:
        """Get random delay before processing next message (human-like)."""
        # Base delay with randomization
        base_delay = random.uniform(MIN_MESSAGE_DELAY, MAX_MESSAGE_DELAY)
        
        # Add occasional long pauses to simulate human behavior
        if random.random() < 0.1:  # 10% chance
            logger.info(f"⏸️ Taking human-like pause ({PAUSE_DURATION[0]}-{PAUSE_DURATION[1]}s)...")
            base_delay = random.uniform(*PAUSE_DURATION)
        
        return base_delay
    
    async def check_join_rate(self) -> bool:
        """Check if we can join another channel."""
        redis = await get_redis()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        join_key = f"joins:{self.session_name}:{today}"
        
        limits = await self.get_limits()
        current_joins = await redis.get(join_key)
        current_joins = int(current_joins) if current_joins else 0
        
        if current_joins >= limits["max_joins_per_day"]:
            logger.warning(
                f"⚠️ Join rate limit reached: {current_joins}/"
                f"{limits['max_joins_per_day']} per day"
            )
            return False
        
        return True


class FloodWaitHandler:
    """Handle Telegram FloodWait errors globally."""
    
    def __init__(self, session_name: str):
        self.session_name = session_name
        self.flood_key = f"flood_wait:{session_name}"
        self.current_backoff = 1  # Start with 1 second
    
    async def is_under_flood_wait(self) -> bool:
        """Check if account is currently under flood wait."""
        redis = await get_redis()
        flood_time = await redis.get(self.flood_key)
        
        if flood_time:
            remaining = float(flood_time) - datetime.now(timezone.utc).timestamp()
            if remaining > 0:
                logger.warning(f"🚫 Still under flood wait: {remaining:.0f}s remaining")
                return True
            else:
                await redis.delete(self.flood_key)
        
        return False
    
    async def handle_flood_wait(self, error: FloodWaitError) -> float:
        """
        Handle FloodWaitError with exponential backoff.
        Returns the wait time in seconds.
        """
        wait_time = error.seconds if hasattr(error, 'seconds') else 60
        
        # Exponential backoff
        self.current_backoff = min(
            self.current_backoff * FLOOD_BACKOFF_MULTIPLIER,
            FLOOD_MAX_BACKOFF
        )
        
        # Add some randomization to prevent thundering herd
        actual_wait = wait_time + random.uniform(0, self.current_backoff)
        
        # Store in Redis
        redis = await get_redis()
        resume_time = datetime.now(timezone.utc).timestamp() + actual_wait
        await redis.set(self.flood_key, resume_time, ex=int(actual_wait) + 60)
        
        logger.error(f"🚫 FloodWait detected! Waiting {actual_wait:.0f}s (server requested {wait_time}s)")
        
        return actual_wait
    
    async def wait_if_flood(self):
        """Wait if under flood wait."""
        redis = await get_redis()
        flood_time = await redis.get(self.flood_key)
        
        if flood_time:
            remaining = float(flood_time) - datetime.now(timezone.utc).timestamp()
            if remaining > 0:
                logger.warning(f"⏳ Waiting for flood clearance: {remaining:.0f}s...")
                await asyncio.sleep(remaining + 1)  # +1s buffer
                await redis.delete(self.flood_key)


class BehaviorRandomizer:
    """Randomize behavior to mimic human activity."""
    
    @staticmethod
    def randomize_message_order(messages: list) -> list:
        """Randomize order of message processing."""
        shuffled = messages.copy()
        random.shuffle(shuffled)
        return shuffled
    
    @staticmethod
    async def get_user_agent() -> str:
        """Get random user agent (desktop/mobile)."""
        agents = [
            "TelegramDesktop/4.9.5",
            "TelegramAndroid/10.10.1",
            "TelegramiOS/10.10.1",
        ]
        return random.choice(agents)
    
    @staticmethod
    async def get_random_active_time() -> bool:
        """
        Simulate human activity patterns.
        Return True if should process messages, False if should idle.
        """
        hour = datetime.now().hour
        
        # Sleep pattern: 0-6 AM (low activity)
        if 0 <= hour < 6:
            return random.random() < 0.1  # 10% activity
        
        # Work hours: 9-17 (high activity)
        elif 9 <= hour < 17:
            return random.random() < 0.8  # 80% activity
        
        # Evening: 17-23 (medium activity)
        else:
            return random.random() < 0.5  # 50% activity


class AccountHealthMonitor:
    """Monitor account health and detect suspicious activity."""
    
    def __init__(self, client, session_name: str):
        self.client = client
        self.session_name = session_name
        self.health_key = f"health:{session_name}"
    
    async def check_health(self) -> Dict:
        """
        Check account health status.
        Returns: {"status": "healthy|warning|danger", "issues": [...]}
        """
        issues = []
        redis = await get_redis()
        
        try:
            # Try to get account info
            me = await self.client.get_me()
            
            # Check 1: Account accessibility
            if not me:
                issues.append("Cannot access account info")
            
            # Check 2: Flood wait
            flood_key = f"flood_wait:{self.session_name}"
            if await redis.get(flood_key):
                issues.append("Account under flood wait")
            
            # Check 3: Connection stability
            # (TelegramClient auto-handles this)
            
            if not issues:
                status = "healthy"
            elif len(issues) == 1:
                status = "warning"
            else:
                status = "danger"
            
            # Save to Redis
            health_info = {
                "status": status,
                "issues": issues,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "user_id": me.id if me else None,
                "username": me.username if me else None
            }
            await redis.set(self.health_key, json.dumps(health_info), ex=86400)
            
            if issues:
                logger.warning(f"⚠️ Account health: {status} - Issues: {issues}")
            else:
                logger.info("✅ Account health: healthy")
            
            return health_info
            
        except AuthKeyUnregisteredError:
            logger.critical("❌ Auth key unregistered - Session may be banned!")
            return {"status": "danger", "issues": ["Auth key unregistered (BANNED?)"]}
        
        except UnauthorizedError:
            logger.critical("❌ Unauthorized - Account access denied!")
            return {"status": "danger", "issues": ["Unauthorized access"]}
        
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            return {"status": "unknown", "issues": [str(e)]}
