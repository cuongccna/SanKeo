import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, delete
from src.common.logger import get_logger
from src.common.redis_client import get_redis
from src.database.db import AsyncSessionLocal
from src.database.models import UserTemplateSubscription, AnalysisTemplate, User, FilterRule, PlanType
from src.worker.analyzers import template_processor

logger = get_logger("scheduler")

QUEUE_NOTIFICATIONS = "queue:notifications"
FREE_MAX_KEYWORDS = 3  # Giới hạn từ khóa cho gói FREE

class TemplateScheduler:
    def __init__(self):
        self.is_running = False
        self.last_expiry_check = None

    async def start(self):
        """Start the scheduler loop."""
        self.is_running = True
        logger.info("⏳ Template Scheduler started.")
        while self.is_running:
            try:
                await self.check_subscriptions()
                
                # Check expired VIP users every 10 minutes
                await self.check_expired_vip_users()
                
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
                    # Generate Report ONCE (Returns dict with text)
                    report_result = await template_processor.process_template(code)
                    
                    if report_result:
                        report_text = report_result.get("text", "")
                        
                        # Send to all users
                        for sub in subs:
                            notification = {
                                "user_id": sub.user_id,
                                "message": report_text,
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

    async def check_expired_vip_users(self):
        """
        Check for expired VIP users and downgrade them to FREE.
        - Delete all their keywords (reset)
        - Change plan_type to FREE
        - Notify user to add keywords for FREE plan
        """
        now = datetime.now(timezone.utc)
        
        # Only check every 10 minutes to reduce DB load
        if self.last_expiry_check:
            if (now - self.last_expiry_check).total_seconds() < 600:  # 10 minutes
                return
        
        self.last_expiry_check = now
        logger.info("🔍 Checking for expired VIP users...")
        
        async with AsyncSessionLocal() as session:
            # Find all VIP/BUSINESS users whose expiry_date has passed
            stmt = select(User).where(
                User.plan_type.in_([PlanType.VIP, PlanType.BUSINESS]),
                User.expiry_date.isnot(None),
                User.expiry_date < now
            )
            result = await session.execute(stmt)
            expired_users = result.scalars().all()
            
            if not expired_users:
                return
            
            logger.info(f"📉 Found {len(expired_users)} expired VIP users")
            redis = await get_redis()
            
            for user in expired_users:
                try:
                    old_plan = user.plan_type
                    
                    # 1. Delete all keywords for this user (reset)
                    await session.execute(
                        delete(FilterRule).where(FilterRule.user_id == user.id)
                    )
                    
                    # 2. Downgrade to FREE
                    user.plan_type = PlanType.FREE
                    user.expiry_date = None  # Clear expiry
                    
                    # 3. Notify user
                    notification = {
                        "user_id": user.id,
                        "message": (
                            "⚠️ **Gói VIP của bạn đã hết hạn!**\n\n"
                            "Tài khoản đã được chuyển về gói **FREE**.\n\n"
                            "📝 **Các từ khóa cũ đã được xóa.**\n"
                            f"Bạn có thể thêm tối đa **{FREE_MAX_KEYWORDS} từ khóa** cho gói FREE.\n\n"
                            "👉 Dùng lệnh /add hoặc bấm nút **\"Thêm từ khóa\"** để thêm lại.\n"
                            "💎 Nâng cấp VIP để có từ khóa không giới hạn!"
                        ),
                        "type": "VIP_EXPIRED"
                    }
                    await redis.lpush(QUEUE_NOTIFICATIONS, json.dumps(notification))
                    
                    logger.info(f"⬇️ Downgraded user {user.id} from {old_plan} to FREE, keywords reset")
                    
                except Exception as e:
                    logger.error(f"Error downgrading user {user.id}: {e}")
            
            await session.commit()
            logger.info(f"✅ Processed {len(expired_users)} expired users")


template_scheduler = TemplateScheduler()
