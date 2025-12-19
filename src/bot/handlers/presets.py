from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import FilterRule, User, PlanType

router = Router()

# Constants (Should match main.py)
FREE_MAX_KEYWORDS = 3

PRESETS = {
    "CRYPTO_GEM": ['hidden gem', 'low cap', 'whitelist', 'private sale', 'presale'],
    "FREELANCE_IT": ['tuyển dụng python', 'việc làm remote', 'cần tìm dev', 'hiring backend'],
    "AIRDROP": ['airdrop', 'gleam.io', 'testnet', 'retroactive']
}

PRESET_NAMES = {
    "CRYPTO_GEM": "💎 Crypto Gem",
    "FREELANCE_IT": "💻 Freelance IT",
    "AIRDROP": "🎁 Airdrop"
}

@router.callback_query(F.data == "preset_libraries")
async def show_presets(callback: types.CallbackQuery):
    """Show list of preset libraries."""
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"apply_preset:{key}")]
        for key, name in PRESET_NAMES.items()
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="back_to_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        "📚 **Kho từ khóa mẫu**\n\n"
        "Chọn một bộ từ khóa để thêm nhanh vào danh sách theo dõi của bạn:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("apply_preset:"))
async def apply_preset(callback: types.CallbackQuery):
    """Apply selected preset to user's filter rules."""
    preset_key = callback.data.split(":")[1]
    keywords = PRESETS.get(preset_key, [])
    
    if not keywords:
        await callback.answer("Bộ từ khóa không tồn tại!", show_alert=True)
        return

    user_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        # Check user plan limits
        user = await session.get(User, user_id)
        if not user:
            await callback.answer("Lỗi: Không tìm thấy thông tin người dùng.", show_alert=True)
            return

        # Get current keyword count
        current_rules_result = await session.execute(select(FilterRule).where(FilterRule.user_id == user_id))
        current_rules = current_rules_result.scalars().all()
        current_count = len(current_rules)
        
        # Check limits for FREE users
        if user.plan_type == PlanType.FREE:
            remaining_slots = FREE_MAX_KEYWORDS - current_count
            
            # If user is already full
            if remaining_slots <= 0:
                 await callback.answer(f"⚠️ Bạn đang dùng gói FREE (tối đa {FREE_MAX_KEYWORDS} từ khóa). Vui lòng nâng cấp VIP để thêm bộ này!", show_alert=True)
                 return
            
            # If preset is larger than remaining slots
            # We will try to add as many as possible or block? 
            # Let's block to keep it simple and encourage upgrade, as partial adds might be confusing.
            # However, checking if the *new unique* keywords fit is complex.
            # Let's just check raw count vs remaining slots for simplicity.
            if len(keywords) > remaining_slots:
                 await callback.answer(f"⚠️ Bộ này có {len(keywords)} từ khóa. Bạn chỉ còn {remaining_slots} chỗ trống. Vui lòng nâng cấp VIP!", show_alert=True)
                 return

        added_count = 0
        existing_keywords = {rule.keyword for rule in current_rules}
        
        for kw in keywords:
            if kw not in existing_keywords:
                session.add(FilterRule(user_id=user_id, keyword=kw))
                added_count += 1
                existing_keywords.add(kw) # Update local set to prevent duplicates within the loop if any
        
        if added_count > 0:
            await session.commit()
            await callback.answer(f"✅ Đã thêm {added_count} từ khóa từ bộ {PRESET_NAMES[preset_key]}!", show_alert=True)
        else:
            await callback.answer("⚠️ Tất cả từ khóa trong bộ này đã có trong danh sách của bạn.", show_alert=True)
            
    # Return to preset menu
    await show_presets(callback)
