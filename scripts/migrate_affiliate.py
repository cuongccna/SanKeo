import asyncio
import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import AsyncSessionLocal

async def migrate():
    print("Starting migration for Affiliate System...")
    async with AsyncSessionLocal() as session:
        try:
            # Add referrer_id column
            print("Adding referrer_id column...")
            await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_id BIGINT;"))
            
            # Add commission_balance column
            print("Adding commission_balance column...")
            await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS commission_balance FLOAT DEFAULT 0.0;"))
            
            await session.commit()
            print("Migration completed successfully!")
        except Exception as e:
            print(f"Migration failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(migrate())
