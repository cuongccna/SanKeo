import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import AnalysisTemplate
from src.common.logger import get_logger
from src.common.template_registry import TEMPLATE_CONFIG

logger = get_logger("seed_templates")

async def seed_templates():
    async with AsyncSessionLocal() as session:
        logger.info("Starting template seeding...")
        
        for code, config in TEMPLATE_CONFIG.items():
            # Determine tags based on code or config (simple logic for now)
            tags = ["SIGNAL"] 
            if "WHALE" in code or "ONCHAIN" in code:
                tags.append("ONCHAIN")
            if "GEM" in code:
                tags.append("LOWCAP")
            if "NEWS" in code or "LISTING" in code:
                tags.append("NEWS_VIP")

            template_data = {
                "code": code,
                "name": config["name_vi"], # Use Vietnamese name for UI
                "required_tags": tags,
                "time_window_minutes": 60, # Default 60 mins
                "prompt_template": config["ai_prompt"]
            }

            # Check if exists
            stmt = select(AnalysisTemplate).where(AnalysisTemplate.code == code)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"Updating template: {code}")
                existing.name = template_data["name"]
                existing.prompt_template = template_data["prompt_template"]
                # existing.required_tags = template_data["required_tags"] # Optional: update tags
            else:
                logger.info(f"Creating new template: {code}")
                new_template = AnalysisTemplate(**template_data)
                session.add(new_template)
        
        await session.commit()
        logger.info("Template seeding completed successfully.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_templates())
