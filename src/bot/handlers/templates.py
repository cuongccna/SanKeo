from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, delete

from src.database.db import AsyncSessionLocal
from src.database.models import AnalysisTemplate, User, PlanType, UserTemplateSubscription
from src.worker.analyzers import template_processor

router = Router()

@router.message(Command("templates"))
async def cmd_templates(message: types.Message):
    # Check VIP/Business
    async with AsyncSessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        if not user or user.plan_type not in [PlanType.VIP, PlanType.BUSINESS]:
            await message.answer("⚠️ Tính năng này chỉ dành cho gói VIP/Business.")
            return
        
        # Get templates
        result = await session.execute(select(AnalysisTemplate))
        templates = result.scalars().all()

        # Get user subscriptions
        sub_result = await session.execute(
            select(UserTemplateSubscription.template_code)
            .where(UserTemplateSubscription.user_id == message.from_user.id)
        )
        subscribed_codes = sub_result.scalars().all()

    if not templates:
        await message.answer("Hiện chưa có template nào.")
        return

    builder = InlineKeyboardBuilder()
    for t in templates:
        is_sub = t.code in subscribed_codes
        status_icon = "✅" if is_sub else "❌"
        action_text = "Hủy đăng ký" if is_sub else "Đăng ký"
        
        # Button format: [✅ Whale Hunting]
        builder.button(text=f"{status_icon} {t.name}", callback_data=f"tpl_toggle_{t.code}")
        
    builder.adjust(1)
    
    text = """
📊 **Smart AI Templates (Auto-Report)**

Chọn template để **Đăng ký/Hủy đăng ký**.
Hệ thống sẽ tự động gửi báo cáo định kỳ cho bạn.
    """
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("tpl_toggle_"))
async def on_template_toggle(callback: types.CallbackQuery):
    code = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        # Check if subscribed
        result = await session.execute(
            select(UserTemplateSubscription)
            .where(UserTemplateSubscription.user_id == user_id)
            .where(UserTemplateSubscription.template_code == code)
        )
        subscription = result.scalar_one_or_none()
        
        if subscription:
            # Unsubscribe
            await session.delete(subscription)
            await session.commit()
            msg = f"❌ Đã hủy đăng ký template `{code}`."
        else:
            # Subscribe
            new_sub = UserTemplateSubscription(user_id=user_id, template_code=code)
            session.add(new_sub)
            await session.commit()
            msg = f"✅ Đã đăng ký template `{code}`.\nBáo cáo sẽ được gửi định kỳ."
            
            # Optional: Trigger first run immediately?
            # For now, let the scheduler handle it (it will run within 1 min because last_sent_at is None)

    await callback.answer(msg)
    # Refresh the menu
    await cmd_templates(callback.message)
