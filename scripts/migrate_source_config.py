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
        # 1. Check if 'tags' column exists using information_schema (Safe check)
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='source_configs' AND column_name='tags'
        """))
        tags_exists = result.scalar() is not None

        if not tags_exists:
            print("⚠️ Column 'tags' missing. Adding it...")
            await conn.execute(text("ALTER TABLE source_configs ADD COLUMN tags JSONB DEFAULT '[]'"))
            print("✅ Added column 'tags'.")
        else:
            print("✅ Column 'tags' already exists.")

        # 2. Check if 'tag' column exists (old column)
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='source_configs' AND column_name='tag'
        """))
        tag_exists = result.scalar() is not None
        
        if tag_exists:
            print("⚠️ Found old column 'tag'. Migrating data...")
            # Migrate data: tags = [tag]
            await conn.execute(text("""
                UPDATE source_configs 
                SET tags = jsonb_build_array(tag) 
                WHERE tag IS NOT NULL AND (tags IS NULL OR jsonb_array_length(tags) = 0)
            """))
            print("✅ Data migrated from 'tag' to 'tags'.")

    print("✅ Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
