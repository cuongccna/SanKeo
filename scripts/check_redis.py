import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.redis_client import get_redis

async def main():
    redis = await get_redis()
    keys = await redis.keys("*")
    print(f"Found {len(keys)} keys:")
    for key in keys:
        value = await redis.get(key)
        print(f"{key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())
