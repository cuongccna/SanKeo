"""
BOT INTERFACE - The Mouth
Xử lý tương tác với người dùng qua Telegram Bot.
"""
import os
import sys
import asyncio
import json
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select, delete
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common.logger import get_logger
from src.common.redis_client import get_redis
from src.database.db import AsyncSessionLocal
from src.database.models import User, FilterRule, PlanType

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logger = get_logger("bot")

# Queue name
QUEUE_NOTIFICATIONS = "queue:notifications"

# Free user limits
FREE_MAX_KEYWORDS = 3

# Initialize bot
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ============ FSM States ============
class AddKeywordState(StatesGroup):
    waiting_for_keyword = State()


# ============ Keyboards ============
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Thêm từ khóa", callback_data="add_keyword")],
        [InlineKeyboardButton(text="📋 Danh sách từ khóa", callback_data="list_keywords")],
        [InlineKeyboardButton(text="💎 Nâng cấp VIP", callback_data="upgrade_vip")],
        [InlineKeyboardButton(text="👤 Tài khoản", callback_data="my_account")],
    ])


def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="back_to_menu")],
    ])


# ============ Helpers ============
async def get_or_create_user(user_id: int, username: str = None) -> User:
    """Get user from DB or create new one."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(id=user_id, username=username, plan_type=PlanType.FREE)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"New user created: {user_id} (@{username})")
        
        return user


async def get_user_keywords(user_id: int) -> list[FilterRule]:
    """Get all keywords for a user."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FilterRule).where(FilterRule.user_id == user_id)
        )
        return result.scalars().all()


async def count_user_keywords(user_id: int) -> int:
    """Count keywords for a user."""
    keywords = await get_user_keywords(user_id)
    return len(keywords)


# ============ Commands ============
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Handle /start command."""
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    
    welcome_text = f"""
🎯 **Chào mừng đến với Personal Alpha Hunter!**

Bot sẽ giúp bạn:
• Theo dõi từ khóa từ hàng ngàn nhóm Telegram
• Nhận thông báo real-time khi có tin nhắn match

📊 **Tài khoản của bạn:**
• Gói: {'💎 VIP' if user.plan_type == PlanType.VIP else '🆓 FREE'}
• Giới hạn từ khóa: {FREE_MAX_KEYWORDS if user.plan_type == PlanType.FREE else '∞'}

Chọn chức năng bên dưới:
"""
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")


@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    """Handle /add command."""
    await message.answer("📝 Nhập từ khóa bạn muốn theo dõi:\n\n_Ví dụ: ETH, BTC, Recruit_", parse_mode="Markdown")
    await state.set_state(AddKeywordState.waiting_for_keyword)


@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    """Handle /list command."""
    keywords = await get_user_keywords(message.from_user.id)
    
    if not keywords:
        await message.answer("📋 Bạn chưa có từ khóa nào.\n\nDùng /add để thêm từ khóa mới.")
        return
    
    text = "📋 **Danh sách từ khóa của bạn:**\n\n"
    for i, kw in enumerate(keywords, 1):
        status = "✅" if kw.is_active else "⏸️"
        text += f"{i}. {status} `{kw.keyword}`\n"
    
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("pay"))
async def cmd_pay(message: types.Message):
    """Handle /pay command."""
    user_id = message.from_user.id
    
    payment_text = f"""
💎 **Nâng cấp VIP - 50.000đ/tháng**

✅ Không giới hạn từ khóa
✅ Không giới hạn thông báo/ngày
✅ Ưu tiên xử lý

📱 **Chuyển khoản:**
• Ngân hàng: **VIETCOMBANK**
• STK: **1234567890**
• Tên: **NGUYEN VAN A**
• Nội dung: `VIP {user_id}`

⚡ Sau khi chuyển khoản, hệ thống sẽ tự động kích hoạt VIP trong 1-2 phút.
"""
    await message.answer(payment_text, reply_markup=get_back_keyboard(), parse_mode="Markdown")


# ============ Callbacks ============
@dp.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Handle back to menu."""
    await state.clear()
    await callback.message.edit_text(
        "🎯 **Menu chính**\n\nChọn chức năng:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "add_keyword")
async def callback_add_keyword(callback: CallbackQuery, state: FSMContext):
    """Handle add keyword button."""
    user = await get_or_create_user(callback.from_user.id)
    keyword_count = await count_user_keywords(callback.from_user.id)
    
    # Check limit for FREE users
    if user.plan_type == PlanType.FREE and keyword_count >= FREE_MAX_KEYWORDS:
        await callback.message.edit_text(
            f"⚠️ **Đã đạt giới hạn!**\n\nGói FREE chỉ cho phép {FREE_MAX_KEYWORDS} từ khóa.\n\nNâng cấp VIP để thêm không giới hạn!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Nâng cấp VIP", callback_data="upgrade_vip")],
                [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="back_to_menu")],
            ]),
            parse_mode="Markdown"
        )
        return
    
    await callback.message.edit_text(
        "📝 **Thêm từ khóa**\n\nNhập từ khóa bạn muốn theo dõi:\n\n_Hỗ trợ Regex. Ví dụ: ETH|BTC, [Rr]ecruit_",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AddKeywordState.waiting_for_keyword)


@dp.callback_query(F.data == "list_keywords")
async def callback_list_keywords(callback: CallbackQuery):
    """Handle list keywords button."""
    keywords = await get_user_keywords(callback.from_user.id)
    
    if not keywords:
        await callback.message.edit_text(
            "📋 Bạn chưa có từ khóa nào.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Thêm từ khóa", callback_data="add_keyword")],
                [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="back_to_menu")],
            ])
        )
        return
    
    text = "📋 **Danh sách từ khóa:**\n\n"
    buttons = []
    
    for i, kw in enumerate(keywords, 1):
        status = "✅" if kw.is_active else "⏸️"
        text += f"{i}. {status} `{kw.keyword}`\n"
        buttons.append([InlineKeyboardButton(text=f"🗑️ Xóa: {kw.keyword[:20]}", callback_data=f"delete_kw:{kw.id}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data="back_to_menu")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@dp.callback_query(F.data.startswith("delete_kw:"))
async def callback_delete_keyword(callback: CallbackQuery):
    """Handle delete keyword."""
    keyword_id = int(callback.data.split(":")[1])
    
    async with AsyncSessionLocal() as session:
        await session.execute(delete(FilterRule).where(FilterRule.id == keyword_id))
        await session.commit()
    
    await callback.answer("✅ Đã xóa từ khóa!")
    await callback_list_keywords(callback)


@dp.callback_query(F.data == "upgrade_vip")
async def callback_upgrade_vip(callback: CallbackQuery):
    """Handle upgrade VIP button."""
    await cmd_pay(callback.message)


@dp.callback_query(F.data == "my_account")
async def callback_my_account(callback: CallbackQuery):
    """Handle my account button."""
    user = await get_or_create_user(callback.from_user.id)
    keyword_count = await count_user_keywords(callback.from_user.id)
    
    expiry_text = ""
    if user.plan_type == PlanType.VIP and user.expiry_date:
        expiry_text = f"\n• Hết hạn: {user.expiry_date.strftime('%d/%m/%Y')}"
    
    text = f"""
👤 **Thông tin tài khoản**

• ID: `{user.id}`
• Username: @{user.username or 'N/A'}
• Gói: {'💎 VIP' if user.plan_type == PlanType.VIP else '🆓 FREE'}{expiry_text}
• Số từ khóa: {keyword_count}{'/' + str(FREE_MAX_KEYWORDS) if user.plan_type == PlanType.FREE else ''}
• Ngày tham gia: {user.created_at.strftime('%d/%m/%Y') if user.created_at else 'N/A'}
"""
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")


# ============ FSM Handlers ============
@dp.message(AddKeywordState.waiting_for_keyword)
async def process_add_keyword(message: types.Message, state: FSMContext):
    """Process keyword input."""
    keyword = message.text.strip()
    
    if not keyword:
        await message.answer("⚠️ Từ khóa không được để trống!")
        return
    
    if len(keyword) > 100:
        await message.answer("⚠️ Từ khóa quá dài (tối đa 100 ký tự)!")
        return
    
    # Add to database
    async with AsyncSessionLocal() as session:
        new_rule = FilterRule(
            user_id=message.from_user.id,
            keyword=keyword,
            is_active=True
        )
        session.add(new_rule)
        await session.commit()
    
    await state.clear()
    await message.answer(
        f"✅ Đã thêm từ khóa: `{keyword}`\n\nBạn sẽ nhận thông báo khi có tin nhắn chứa từ khóa này.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    logger.info(f"User {message.from_user.id} added keyword: {keyword}")


# ============ Notification Worker ============
async def notification_worker():
    """Background task to send notifications to users."""
    redis = await get_redis()
    logger.info("Notification Worker started...")
    
    while True:
        try:
            result = await redis.brpop(QUEUE_NOTIFICATIONS, timeout=1)
            
            if result:
                _, data = result
                notification = json.loads(data)
                
                user_id = notification["user_id"]
                msg_data = notification["message"]
                keyword = notification["matched_keyword"]
                
                # Format notification message
                chat_title = msg_data.get("chat_title", "Unknown")
                text = msg_data.get("text", "")[:500]  # Truncate long messages
                message_link = msg_data.get("message_link", "")
                
                notification_text = f"""
🔔 **Match: `{keyword}`**

📢 **Từ:** {chat_title}

💬 {text}

{"🔗 " + message_link if message_link else ""}
"""
                
                try:
                    await bot.send_message(user_id, notification_text, parse_mode="Markdown")
                    logger.debug(f"Notification sent to {user_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification to {user_id}: {e}")
                
        except Exception as e:
            logger.error(f"Notification worker error: {e}")
            await asyncio.sleep(1)


# ============ Main ============
async def main():
    """Main entry point for Bot Service."""
    logger.info("=" * 50)
    logger.info("BOT INTERFACE - Starting...")
    logger.info("=" * 50)
    
    # Test Redis connection
    redis = await get_redis()
    await redis.ping()
    logger.info("Redis connection: OK")
    
    # Start notification worker as background task
    asyncio.create_task(notification_worker())
    
    # Get bot info
    me = await bot.get_me()
    logger.info(f"Bot started: @{me.username}")
    
    # Start polling
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
