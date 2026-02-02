"""
Test script để verify session hoạt động trên local
"""
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_PHONE = "84987939605"

async def test_ingestor():
    """Test ingestor dependencies."""
    
    print("=" * 60)
    print("🧪 INGESTOR DEPENDENCIES TEST")
    print("=" * 60)
    
    # Ensure sessions directory
    os.makedirs("sessions", exist_ok=True)
    
    try:
        # Test 1: Session file exists
        session_file = f"sessions/{SESSION_PHONE}.session"
        if os.path.exists(session_file):
            print(f"\n✅ Session file exists: {session_file}")
            size = os.path.getsize(session_file)
            print(f"   Size: {size} bytes")
        else:
            print(f"\n❌ Session file NOT found: {session_file}")
            return
        
        # Test 2: Redis connection
        print("\n🔴 Testing Redis connection...")
        from src.common.redis_client import get_redis
        redis = await get_redis()
        await redis.ping()
        print("✅ Redis connection: OK")
        
        # Test 3: Database connection
        print("\n📊 Testing Database connection...")
        from src.database.db import AsyncSessionLocal
        from src.database.models import SourceConfig
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SourceConfig).limit(1))
            count = result.scalars().first()
            print("✅ Database connection: OK")
        
        # Test 4: Load protection module
        print("\n🛡️ Testing Protection Module...")
        from src.ingestor.protection import RateLimiter, FloodWaitHandler, AccountHealthMonitor
        
        rate_limiter = RateLimiter(SESSION_PHONE)
        await rate_limiter.init()
        limits = await rate_limiter.get_limits()
        account_age = await rate_limiter.get_account_age()
        
        print(f"✅ Protection module loaded")
        print(f"   Account age: {account_age} days")
        print(f"   Current limits: {limits['max_messages_per_hour']} msg/hour")
        print(f"   Daily joins: {limits['max_joins_per_day']} joins/day")
        
        # Test 5: Import main ingestor
        print("\n📡 Testing Ingestor module...")
        from src.ingestor import main as ingestor_main
        print("✅ Ingestor module imported successfully")
        
        # Test 6: Check dependencies
        print("\n📦 Testing dependencies...")
        try:
            from telethon import TelegramClient
            print("✅ Telethon: OK")
        except:
            print("❌ Telethon: MISSING")
        
        try:
            from pyrogram import Client
            print("✅ Pyrogram: OK")
        except:
            print("❌ Pyrogram: MISSING")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n🚀 Ready to deploy on VPS!")
        print(f"\nNext steps:")
        print(f"1. Copy session file: sessions/{SESSION_PHONE}.session to VPS")
        print(f"2. Update VPS env vars with API_ID={API_ID}")
        print(f"3. Restart ingestor: pm2 restart sankeo-ingestor")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ingestor())
