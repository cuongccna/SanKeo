import json
import time
from datetime import datetime, timedelta
from sqlalchemy import select
from src.common.logger import logger
from src.common.redis_client import get_redis
from src.database.db import AsyncSessionLocal
from src.database.models import AnalysisTemplate
from src.common.ai_client import ai_client

class TemplateProcessor:
    def __init__(self):
        self.redis = None

    async def get_redis_conn(self):
        if not self.redis:
            self.redis = await get_redis()
        return self.redis

    async def collect_data(self, template_code: str):
        """
        Query Redis/DB to get messages for the template within its time window.
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AnalysisTemplate).where(AnalysisTemplate.code == template_code))
            template = result.scalar_one_or_none()
        
        if not template:
            logger.error(f"Template {template_code} not found")
            return None, None

        redis = await self.get_redis_conn()
        
        # Calculate time window
        now = time.time()
        window_start = now - (template.time_window_minutes * 60)
        
        all_messages = []
        
        # Collect messages from all required tags
        # Assuming messages are stored in Redis Sorted Set: analysis_buffer:{tag}
        # Score: timestamp, Member: message_json
        if isinstance(template.required_tags, list):
            tags = template.required_tags
        else:
            try:
                tags = json.loads(template.required_tags)
            except:
                tags = []

        for tag in tags:
            key = f"analysis_buffer:{tag}"
            # Get messages within window
            messages = await redis.zrangebyscore(key, window_start, now)
            for msg_str in messages:
                try:
                    msg_data = json.loads(msg_str)
                    # Extract text content
                    if isinstance(msg_data, dict):
                        text = msg_data.get('text', '') or msg_data.get('message', '')
                        if text:
                            all_messages.append(text)
                    else:
                        all_messages.append(str(msg_data))
                except:
                    all_messages.append(str(msg_str))

        return all_messages, template

    async def process_template(self, template_code: str):
        messages, template = await self.collect_data(template_code)
        
        if not messages or not template:
            return None

        # Logic: Check if enough messages
        if len(messages) < 3:
            logger.info(f"Not enough messages for template {template_code} ({len(messages)} < 3). Skipping.")
            return None

        logger.info(f"Generating report for {template_code} with {len(messages)} messages.")
        
        # Call AI
        report = await ai_client.generate_template_report(messages, template.name)
        return report

    async def buffer_message(self, tag: str, message_data: dict):
        """
        Store message in Redis buffer for later analysis.
        """
        redis = await self.get_redis_conn()
        key = f"analysis_buffer:{tag}"
        timestamp = time.time()
        
        # Store as JSON
        member = json.dumps(message_data)
        
        # Add to Sorted Set
        await redis.zadd(key, {member: timestamp})
        
        # Set expiry (e.g., 24 hours) to prevent infinite growth
        await redis.expire(key, 86400)

template_processor = TemplateProcessor()

