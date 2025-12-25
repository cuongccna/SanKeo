import asyncio
import json
import time
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete
from src.common.logger import get_logger
from src.common.redis_client import get_redis
from src.database.db import AsyncSessionLocal
from src.database.models import UserTemplateSubscription, AnalysisTemplate
from src.worker.analyzers import template_processor

logger = get_logger("scheduler")

QUEUE_NOTIFICATIONS = "queue:notifications"

class TemplateScheduler:
    def __init__(self):
        self.is_running = False

    async def start(self):
        """Start the scheduler loop."""
        self.is_running = True
        logger.info("⏳ Template Scheduler started.")
        while self.is_running:
            try:
                await self.check_subscriptions()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            # Check every minute
            await asyncio.sleep(60)

    async def stop(self):
        self.is_running = False
        logger.info("Template Scheduler stopped.")

    async def check_subscriptions(self):
        """
        Check DB for subscriptions that are due.
        Optimized to group by template to reduce AI calls.
        """
        async with AsyncSessionLocal() as session:
            # 1. Get all active subscriptions joined with Template info
            stmt = (
                select(UserTemplateSubscription, AnalysisTemplate)
                .join(AnalysisTemplate, UserTemplateSubscription.template_code == AnalysisTemplate.code)
            )
            result = await session.execute(stmt)
            subscriptions = result.all()

            now = datetime.utcnow()
            redis = await get_redis()

            # Group by template_code
            # { "WHALE_HUNTING": [sub1, sub2, ...], ... }
            due_subscriptions = {}

            for sub, template in subscriptions:
                last_run = sub.last_sent_at or sub.created_at
                if last_run.tzinfo:
                    last_run = last_run.replace(tzinfo=None)
                
                next_run = last_run + timedelta(minutes=template.time_window_minutes)
                
                if now >= next_run:
                    if template.code not in due_subscriptions:
                        due_subscriptions[template.code] = {
                            "template": template,
                            "subs": []
                        }
                    due_subscriptions[template.code]["subs"].append(sub)

            # Process each template group
            for code, data in due_subscriptions.items():
                template = data["template"]
                subs = data["subs"]
                
                logger.info(f"Processing template {code} for {len(subs)} users...")
                
                try:
                    # Generate Report ONCE (Returns dict with text and image_path)
                    report_result = await template_processor.process_template(code)
                    
                    if report_result:
                        report_text = report_result.get("text", "")
                        image_path = report_result.get("image_path")
                        
                        # Send to all users
                        for sub in subs:
                            notification = {
                                "user_id": sub.user_id,
                                "message": f"🔔 <b>Báo cáo định kỳ: {template.name}</b>\n\n{report_text}",
                                "image_path": image_path,
                                "type": "TEMPLATE_REPORT"
                            }
                            await redis.lpush(QUEUE_NOTIFICATIONS, json.dumps(notification))
                            
                            # Update last_sent_at
                            sub.last_sent_at = now
                            session.add(sub)
                        
                        await session.commit()
                        logger.info(f"Sent report {code} to {len(subs)} users.")
                    else:
                        logger.warning(f"No report generated for {code} (Not enough data?)")
                        
                except Exception as e:
                    logger.error(f"Failed to process template {code}: {e}")

template_scheduler = TemplateScheduler()
