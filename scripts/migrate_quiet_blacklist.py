import asyncio
import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import engine
from src.database.models import Base

async def migrate():
    # 1. Add quiet_start
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS quiet_start TIME"))
            print("Checked/Added quiet_start column")
    except Exception as e:
        print(f"Error adding quiet_start: {e}")

    # 2. Add quiet_end
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS quiet_end TIME"))
            print("Checked/Added quiet_end column")
    except Exception as e:
        print(f"Error adding quiet_end: {e}")

    # 3. Create tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Created missing tables (including blacklisted_channels)")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
