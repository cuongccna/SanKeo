import asyncio
import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import engine
from src.database.models import Base

async def migrate():
    async with engine.begin() as conn:
        # Add columns to users table
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN quiet_start TIME"))
            print("Added quiet_start column")
        except Exception as e:
            print(f"quiet_start column might already exist: {e}")

        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN quiet_end TIME"))
            print("Added quiet_end column")
        except Exception as e:
            print(f"quiet_end column might already exist: {e}")

        # Create blacklisted_channels table
        try:
            await conn.run_sync(Base.metadata.create_all)
            print("Created missing tables (including blacklisted_channels)")
        except Exception as e:
            print(f"Error creating tables: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
