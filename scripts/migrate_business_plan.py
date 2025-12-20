import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import engine
from src.database.models import UserForwardingTarget, Base

async def migrate():
    print("🔄 Migrating Business Plan tables...")
    async with engine.begin() as conn:
        # Create UserForwardingTarget table
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
