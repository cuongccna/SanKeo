import asyncio
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import SourceConfig
from src.common.logger import get_logger

logger = get_logger("seed_data")

SOURCE_DATA = [
    # Group 1: Tin tức Tốc độ (Priority: 10)
    {"chat_id": -1001404987037, "name": "Tree News", "tags": ["NEWS_VIP", "SENTIMENT", "SECURITY"], "priority": 10},
    {"chat_id": -1001138656123, "name": "Binance Announcements", "tags": ["LISTING", "NEWS_VIP"], "priority": 10},
    {"chat_id": -1001404987038, "name": "Wu Blockchain", "tags": ["NEWS_ASIA", "MINING"], "priority": 10},

    # Group 2: On-chain & Cá mập (Priority: 9)
    {"chat_id": -1001134548450, "name": "Whale Alert", "tags": ["ONCHAIN", "WHALE"], "priority": 9},
    {"chat_id": -1001386066226, "name": "CryptoQuant Digest", "tags": ["ONCHAIN", "DATA"], "priority": 9},

    # Group 3: Săn Kèo & Lowcap (Priority: 8)
    {"chat_id": -1001061036437, "name": "ICO Drops", "tags": ["LOWCAP", "IDO"], "priority": 8},
    {"chat_id": -1001170664923, "name": "Coin98 Analytics", "tags": ["NARRATIVE", "AIRDROP"], "priority": 8},

    # Group 4: Tín hiệu & Cộng đồng VN (Priority: 7)
    {"chat_id": -1001140043983, "name": "TradeCoinVietnam", "tags": ["SIGNAL", "KOLS", "SENTIMENT"], "priority": 7},
    {"chat_id": -1001168641477, "name": "HC Capital", "tags": ["SIGNAL", "LOWCAP"], "priority": 7},

    # Group 5: Airdrop (Priority: 6)
    {"chat_id": -1001157076435, "name": "Airdrop Official", "tags": ["AIRDROP", "GUIDE"], "priority": 6},
]

async def seed_source_configs():
    async with AsyncSessionLocal() as session:
        for data in SOURCE_DATA:
            # Check if exists
            result = await session.execute(select(SourceConfig).where(SourceConfig.chat_id == data["chat_id"]))
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"Source {data['name']} ({data['chat_id']}) already exists. Updating...")
                existing.name = data["name"]
                existing.tags = data["tags"]
                existing.priority = data["priority"]
                existing.is_active = True
            else:
                logger.info(f"Creating source {data['name']} ({data['chat_id']})...")
                new_source = SourceConfig(
                    chat_id=data["chat_id"],
                    name=data["name"],
                    tags=data["tags"],
                    priority=data["priority"],
                    is_active=True
                )
                session.add(new_source)
        
        await session.commit()
        logger.info("Source configs seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_source_configs())
