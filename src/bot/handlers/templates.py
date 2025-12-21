from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, delete

from src.database.db import AsyncSessionLocal
from src.database.models import AnalysisTemplate, User, PlanType, UserTemplateSubscription
from src.worker.analyzers import template_processor

router = Router()

@router.message(Command("templates"))
async def cmd_templates(message: types.Message, user_id: int = None):
    # Allow optional user_id override for callback queries
    uid = user_id or message.from_user.id
    
    # Check VIP/Business
    async with AsyncSessionLocal() as session:
        user = await session.get(User, uid)
        if not user or user.plan_type not in [PlanType.VIP, PlanType.BUSINESS]:
            text = "⚠️ Tính năng này chỉ dành cho gói VIP/Business."
            if isinstance(message, types.Message):
                await message.answer(text)
            else:
                # If called from callback (message is actually the message object to edit)
                await message.edit_text(text)
            return
        
        # Get templates
        result = await session.execute(select(AnalysisTemplate))
        templates = result.scalars().all()

        # Get user subscriptions
        sub_result = await session.execute(
            select(UserTemplateSubscription.template_code)
            .where(UserTemplateSubscription.user_id == uid)
        )
        subscribed_codes = sub_result.scalars().all()

    if not templates:
        text = "Hiện chưa có template nào."
        if isinstance(message, types.Message) and not user_id:
             await message.answer(text)
        else:
             await message.edit_text(text)
        return

    builder = InlineKeyboardBuilder()
    for t in templates:
        is_sub = t.code in subscribed_codes
        status_icon = "✅" if is_sub else "❌"
        
        # Button format: [✅ Whale Hunting]
        builder.button(text=f"{status_icon} {t.name}", callback_data=f"tpl_toggle_{t.code}")
    
    # Add Back Button
    builder.button(text="⬅️ Quay lại", callback_data="back_to_menu")
    builder.adjust(1)
    
    text = """
📊 **Smart AI Templates (Auto-Report)**

Chọn template để **Đăng ký/Hủy đăng ký**.
Hệ thống sẽ tự động gửi báo cáo định kỳ cho bạn.
    """
    
    if isinstance(message, types.Message) and not user_id:
        await message.answer(text, reply_markup=builder.as_markup())
    else:
        # Edit existing message if called from callback
        await message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("tpl_toggle_"))
async def on_template_toggle(callback: types.CallbackQuery):
    # Fix: Handle codes with underscores (e.g. WHALE_HUNTING)
    # callback.data is "tpl_toggle_WHALE_HUNTING"
    code = callback.data.replace("tpl_toggle_", "")
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
    await cmd_templates(callback.message, user_id=user_id)
