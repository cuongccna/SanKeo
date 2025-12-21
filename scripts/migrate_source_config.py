import asyncio
import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import engine

async def migrate():
    print("🔄 Migrating SourceConfig table (tag -> tags)...")
    async with engine.begin() as conn:
        # 1. Check if 'tags' column exists
        try:
            await conn.execute(text("SELECT tags FROM source_configs LIMIT 1"))
            print("✅ Column 'tags' already exists.")
        except Exception:
            print("⚠️ Column 'tags' missing. Adding it...")
            await conn.execute(text("ALTER TABLE source_configs ADD COLUMN tags JSONB DEFAULT '[]'"))
            print("✅ Added column 'tags'.")

        # 2. Check if 'tag' column exists (old column)
        try:
            # Check if tag exists by trying to select it
            await conn.execute(text("SELECT tag FROM source_configs LIMIT 1"))
            print("⚠️ Found old column 'tag'. Migrating data...")
            
            # Migrate data: tags = [tag]
            await conn.execute(text("""
                UPDATE source_configs 
                SET tags = jsonb_build_array(tag) 
                WHERE tag IS NOT NULL AND (tags IS NULL OR jsonb_array_length(tags) = 0)
            """))
            print("✅ Data migrated from 'tag' to 'tags'.")
            
            # Optional: Drop old column
            # await conn.execute(text("ALTER TABLE source_configs DROP COLUMN tag"))
            # print("✅ Dropped column 'tag'.")
            
        except Exception as e:
            # 'tag' column likely doesn't exist, which is fine
            print(f"ℹ️ Old column 'tag' not found or error: {e}")

    print("✅ Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
