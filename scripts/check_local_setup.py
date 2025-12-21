import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

from src.database.db import AsyncSessionLocal
from src.database.models import AnalysisTemplate
from sqlalchemy import select

async def check_db():
    print("Checking database content...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AnalysisTemplate))
        templates = result.scalars().all()
        
        if not templates:
            print("❌ No templates found in database!")
        else:
            print(f"✅ Found {len(templates)} templates:")
            for t in templates:
                print(f"  - [{t.code}] {t.name} (Window: {t.time_window_minutes}m)")

async def check_imports():
    print("\nChecking imports...")
    try:
        from src.bot.handlers import templates
        print("✅ src.bot.handlers.templates imported successfully")
    except Exception as e:
        print(f"❌ Failed to import src.bot.handlers.templates: {e}")

    try:
        from src.worker.analyzers import template_processor
        print("✅ src.worker.analyzers imported successfully")
    except Exception as e:
        print(f"❌ Failed to import src.worker.analyzers: {e}")

    try:
        from src.common.ai_client import ai_client
        print("✅ src.common.ai_client imported successfully")
    except Exception as e:
        print(f"❌ Failed to import src.common.ai_client: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
    asyncio.run(check_imports())
