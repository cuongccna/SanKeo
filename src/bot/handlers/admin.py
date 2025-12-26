import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from sqlalchemy import select, func

from src.common.config import settings
from src.database.db import AsyncSessionLocal
from src.database.models import User, PlanType

logger = logging.getLogger("admin")
router = Router()

# Admin Check
def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_ID

# ============ /stats ============
@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    async with AsyncSessionLocal() as session:
        # Total users
        total_users = await session.scalar(select(func.count(User.id)))
        
        # VIP users
        vip_users = await session.scalar(select(func.count(User.id)).where(User.plan_type == PlanType.VIP))
        
        # New users (24h)
        yesterday = datetime.utcnow() - timedelta(days=1)
        new_users = await session.scalar(select(func.count(User.id)).where(User.created_at >= yesterday))

    text = f"""
📊 **Thống kê hệ thống**

👥 **Tổng User:** {total_users}
💎 **User VIP:** {vip_users}
🆕 **User mới (24h):** {new_users}
    """
    await message.answer(text, parse_mode="Markdown")


# ============ /gift ============
@router.message(Command("gift"))
async def cmd_gift(message: types.Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return

    args = command.args
    if not args:
        await message.answer("⚠️ Cú pháp: `/gift <user_id> <days>`", parse_mode="Markdown")
        return

    try:
        parts = args.split()
        target_user_id = int(parts[0])
        days = int(parts[1])
    except (ValueError, IndexError):
        await message.answer("⚠️ Tham số không hợp lệ.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == target_user_id))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ User không tồn tại trong hệ thống.")
            return

        now = datetime.now(timezone.utc)
        if user.plan_type == PlanType.VIP and user.expiry_date and user.expiry_date > now:
            user.expiry_date += timedelta(days=days)
        else:
            user.expiry_date = now + timedelta(days=days)
        
        user.plan_type = PlanType.VIP
        await session.commit()
        
        new_expiry = user.expiry_date.strftime("%d/%m/%Y")
        
    await message.answer(f"✅ Đã tặng {days} ngày VIP cho User `{target_user_id}`.\nHạn mới: {new_expiry}", parse_mode="Markdown")
    
    # Notify user
    try:
        await message.bot.send_message(target_user_id, f"🎁 **Bạn nhận được quà từ Admin!**\n\nĐược cộng thêm **{days} ngày** VIP.\nHạn sử dụng mới: **{new_expiry}**", parse_mode="Markdown")
    except Exception:
        pass


# ============ /broadcast ============
@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    if not message.reply_to_message:
        await message.answer("⚠️ Hãy reply vào tin nhắn cần broadcast.")
        return

    status_msg = await message.answer("⏳ Đang chuẩn bị broadcast...")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.id))
        user_ids = result.scalars().all()

    success_count = 0
    fail_count = 0
    
    for user_id in user_ids:
        try:
            await message.reply_to_message.copy_to(chat_id=user_id)
            success_count += 1
        except Exception as e:
            fail_count += 1
            # logger.error(f"Broadcast failed for {user_id}: {e}")
        
        # Avoid flood limit
        await asyncio.sleep(0.05)
        
        if (success_count + fail_count) % 100 == 0:
            await status_msg.edit_text(f"⏳ Đang gửi... ({success_count}/{len(user_ids)})")

    await status_msg.edit_text(
        f"✅ **Broadcast hoàn tất!**\n\n"
        f"Thành công: {success_count}\n"
        f"Thất bại: {fail_count}",
        parse_mode="Markdown"
    )
