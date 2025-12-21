"""
BOT INTERFACE - The Mouth
Xử lý tương tác với người dùng qua Telegram Bot.
"""
import os
import sys
import asyncio
import json
import random
import re
from urllib.parse import quote
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy import select, delete, func
from dotenv import load_dotenv
from typing import Callable, Dict, Any, Awaitable

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common.logger import get_logger
from src.common.redis_client import get_redis
from src.common.config import settings
from src.common.utils import escape_markdown
from src.database.db import AsyncSessionLocal
from src.database.models import User, FilterRule, PlanType, UserForwardingTarget
from src.bot.handlers import admin, presets, settings as bot_settings, templates

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logger = get_logger("bot")

# Queue name
QUEUE_NOTIFICATIONS = "queue:notifications"
QUEUE_PAYMENT_NOTIFICATIONS = "queue:payment_notifications"

# Free user limits
FREE_MAX_KEYWORDS = 3

# Keyword Validation Config
KEYWORD_BLACKLIST = {
    "kèo", "mua", "bán", "coin", "news", "admin", "anh em", 
    "long", "short", "tp", "sl", "entry", "target", "channel", "group"
}

# Initialize bot
bot = Bot(token=BOT_TOKEN)
storage = RedisStorage.from_url(settings.REDIS_URL)
dp = Dispatcher(storage=storage)

# Register Routers
dp.include_router(admin.router)
dp.include_router(presets.router)
dp.include_router(bot_settings.router)
dp.include_router(templates.router)

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, types.Message):
            logger.info(f"Middleware: Received message: '{event.text}' from {event.from_user.id}")
        return await handler(event, data)

dp.message.middleware(LoggingMiddleware())


# ============ FSM States ============
class AddKeywordState(StatesGroup):
    waiting_for_keyword = State()


# ============ Keyboards ============
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Kho từ khóa mẫu", callback_data="preset_libraries")],
        [InlineKeyboardButton(text="🤖 Smart AI Templates (VIP)", callback_data="smart_templates")],
        [InlineKeyboardButton(text="➕ Thêm từ khóa", callback_data="add_keyword")],
        [InlineKeyboardButton(text="📋 Danh sách từ khóa", callback_data="list_keywords")],
        [InlineKeyboardButton(text="💎 Nâng cấp Gói", callback_data="upgrade_menu")],
        [InlineKeyboardButton(text="🤝 Affiliate (Kiếm tiền)", callback_data="affiliate_info")],
        [InlineKeyboardButton(text="⚙️ Cài đặt", callback_data="settings_menu")],
        [InlineKeyboardButton(text="👤 Tài khoản", callback_data="my_account")],
    ])


def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="back_to_menu")],
    ])


# ============ Helpers ============
async def get_or_create_user(user_id: int, username: str = None, referrer_id: int = None) -> User:
    """Get user from DB or create new one."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            # Prevent self-referral
            if referrer_id == user_id:
                referrer_id = None
                
            user = User(id=user_id, username=username, plan_type=PlanType.FREE, referrer_id=referrer_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"New user created: {user_id} (@{username}) with referrer: {referrer_id}")
            
            # Notify referrer if exists
            if referrer_id:
                try:
                    await bot.send_message(referrer_id, f"🎉 **Chúc mừng!**\nBạn vừa giới thiệu thành công thành viên mới: @{username or user_id}", parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Failed to notify referrer {referrer_id}: {e}")
        
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
@dp.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: types.Message, command: CommandObject):
    """Handle /start with deep link (referral)."""
    args = command.args
    referrer_id = None
    
    if args and args.startswith("ref_"):
        try:
            referrer_id = int(args.replace("ref_", ""))
        except ValueError:
            pass
            
    user = await get_or_create_user(message.from_user.id, message.from_user.username, referrer_id)
    
    plan_display = "🆓 FREE"
    if user.plan_type == PlanType.VIP:
        plan_display = "💎 VIP"
    elif user.plan_type == PlanType.BUSINESS:
        plan_display = "🏢 BUSINESS"
        
    keyword_limit = str(FREE_MAX_KEYWORDS) if user.plan_type == PlanType.FREE else "∞"

    welcome_text = f"""
🎯 **Chào mừng đến với Personal Alpha Hunter!**

Bot sẽ giúp bạn:
• Theo dõi từ khóa từ hàng ngàn nhóm Telegram
• Nhận thông báo real-time khi có tin nhắn match

📊 **Tài khoản của bạn:**
• Gói: {plan_display}
• Giới hạn từ khóa: {keyword_limit}

Chọn chức năng bên dưới:
"""
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Handle /start command."""
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    
    plan_display = "🆓 FREE"
    if user.plan_type == PlanType.VIP:
        plan_display = "💎 VIP"
    elif user.plan_type == PlanType.BUSINESS:
        plan_display = "🏢 BUSINESS"
        
    keyword_limit = str(FREE_MAX_KEYWORDS) if user.plan_type == PlanType.FREE else "∞"

    welcome_text = f"""
🎯 **Chào mừng đến với Personal Alpha Hunter!**

Bot sẽ giúp bạn:
• Theo dõi từ khóa từ hàng ngàn nhóm Telegram
• Nhận thông báo real-time khi có tin nhắn match

📊 **Tài khoản của bạn:**
• Gói: {plan_display}
• Giới hạn từ khóa: {keyword_limit}

Chọn chức năng bên dưới:
"""
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(Command("affiliate"))
async def cmd_affiliate(message: types.Message):
    """Show affiliate info."""
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        balance = user.commission_balance if user else 0.0
        
    text = f"""
🤝 **Chương trình Affiliate (Tiếp thị liên kết)**

🔗 **Link giới thiệu của bạn:**
`{ref_link}`

💰 **Hoa hồng hiện tại:** {balance:,.0f} VND

🎁 **Cơ chế:**
- Nhận ngay **20%** giá trị đơn hàng khi người bạn giới thiệu nâng cấp VIP.
- Hoa hồng được cộng trực tiếp vào số dư.
    """
    await message.answer(text, parse_mode="Markdown")


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
async def cmd_pay(message: types.Message, amount: int = 50000, plan_name: str = "VIP"):
    """Handle /pay command."""
    user_id = message.chat.id  # Use chat.id to be safe if from_user is missing in some contexts, but message.chat.id is reliable for DM
    
    # Bank Info
    BANK_ID = "MB"
    ACCOUNT_NO = "0987939605"
    ACCOUNT_NAME = "NGO VAN CUONG"
    AMOUNT = str(amount)
    
    # Determine content prefix
    prefix = plan_name
    if plan_name == "BUSINESS":
        prefix = "BUS"
        
    CONTENT = f"{prefix} {user_id}"
    
    # Generate QR Code (VietQR)
    qr_url = f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact2.png?amount={AMOUNT}&addInfo={quote(CONTENT)}&accountName={quote(ACCOUNT_NAME)}"
    
    payment_text = f"""
💎 **Nâng cấp {plan_name} - {amount:,.0f}đ/tháng**

✅ Không giới hạn từ khóa
✅ Không giới hạn thông báo/ngày
✅ Ưu tiên xử lý
{ "✅ **Tự động forward tin nhắn vào nhóm riêng**" if plan_name == "BUSINESS" else ""}

👇 **Quét mã QR để thanh toán nhanh:**
• Ngân hàng: **MBank**
• STK: `{ACCOUNT_NO}`
• Tên: **{ACCOUNT_NAME}**
• Nội dung: `{CONTENT}`

⚡ Hệ thống sẽ tự động kích hoạt {plan_name} trong 1-2 phút sau khi nhận được tiền.
"""
    try:
        await message.answer_photo(
            photo=qr_url,
            caption=payment_text,
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to send QR code: {e}")
        # Fallback to text only
        await message.answer(payment_text, reply_markup=get_back_keyboard(), parse_mode="Markdown")


# ============ Callbacks ============
@dp.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Handle back to menu."""
    await state.clear()
    
    # If message has photo, delete and send new text message
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            "🎯 **Menu chính**\n\nChọn chức năng:",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        # If text message, just edit it
        await callback.message.edit_text(
            "🎯 **Menu chính**\n\nChọn chức năng:",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )


@dp.callback_query(F.data == "add_keyword")
async def callback_add_keyword(callback: CallbackQuery, state: FSMContext):
    """Handle add keyword button."""
    await callback.answer()  # Answer callback to remove loading state
    
    user = await get_or_create_user(callback.from_user.id)
    keyword_count = await count_user_keywords(callback.from_user.id)
    
    logger.info(f"User {callback.from_user.id} clicked add_keyword, current count: {keyword_count}")
    
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
        """📝 **Thêm từ khóa**

Nhập từ khóa bạn muốn theo dõi.

💡 **Hướng dẫn:**
- Nhập 1 từ khóa: `Bitcoin`
- Nhập nhiều từ khóa (cách nhau bằng dấu phẩy): `BTC, ETH, SOL`
- Độ dài: 2 - 50 ký tự.
- Không chứa ký tự đặc biệt quá nhiều.

⚠️ **Lưu ý:** Nếu đang ở trong nhóm, hãy **Reply** tin nhắn này để bot nhận được!""",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AddKeywordState.waiting_for_keyword)
    logger.info(f"User {callback.from_user.id} state set to waiting_for_keyword")


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


@dp.callback_query(F.data == "upgrade_menu")
async def callback_upgrade_menu(callback: CallbackQuery):
    """Show upgrade options based on current plan."""
    user = await get_or_create_user(callback.from_user.id)
    
    if user.plan_type == PlanType.BUSINESS:
        text = """
🏢 **Gói hiện tại: BUSINESS**

Bạn đang sử dụng gói cao cấp nhất với đầy đủ quyền lợi:
✅ Không giới hạn từ khóa
✅ Auto-forward tin nhắn
✅ **AI Phân tích chuyên sâu**
✅ Hỗ trợ ưu tiên

Cảm ơn bạn đã đồng hành cùng chúng tôi! ❤️
        """
        buttons = [[InlineKeyboardButton(text="⬅️ Quay lại", callback_data="back_to_menu")]]
        
    elif user.plan_type == PlanType.VIP:
        text = """
💎 **Nâng cấp lên BUSINESS**

Bạn đang là thành viên VIP. Hãy nâng cấp lên BUSINESS để mở khóa:
🚀 **Tự động forward tin nhắn vào Group/Channel riêng**
🧠 **AI Phân tích chuyên sâu & Chi tiết hơn**
✨ Hỗ trợ setup 1-1
        """
        buttons = [
            [InlineKeyboardButton(text="🏢 Nâng cấp BUSINESS (299k)", callback_data="pay_business")],
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="back_to_menu")]
        ]
        
    else:
        text = """
💎 **Chọn gói nâng cấp:**

1️⃣ **Gói VIP (50.000đ/tháng)**
• Không giới hạn từ khóa
• Không giới hạn thông báo
• 🤖 **AI Phân tích cơ bản**
• Ưu tiên xử lý

2️⃣ **Gói BUSINESS (299.000đ/tháng)**
• Tất cả quyền lợi VIP
• **Tự động forward tin nhắn vào Group/Channel riêng**
• 🧠 **AI Phân tích chuyên sâu (Custom Prompt)**
• Hỗ trợ setup riêng
        """
        buttons = [
            [InlineKeyboardButton(text="💎 Chọn VIP (50k)", callback_data="pay_vip")],
            [InlineKeyboardButton(text="🏢 Chọn BUSINESS (299k)", callback_data="pay_business")],
            [InlineKeyboardButton(text="⬅️ Quay lại", callback_data="back_to_menu")]
        ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@dp.callback_query(F.data == "pay_vip")
async def callback_pay_vip(callback: CallbackQuery):
    """Handle pay VIP."""
    try:
        await callback.message.delete()
    except:
        pass
    await cmd_pay(callback.message, amount=50000, plan_name="VIP")


@dp.callback_query(F.data == "pay_business")
async def callback_pay_business(callback: CallbackQuery):
    """Handle pay Business."""
    try:
        await callback.message.delete()
    except:
        pass
    await cmd_pay(callback.message, amount=100000, plan_name="BUSINESS")


@dp.callback_query(F.data == "my_account")
async def callback_my_account(callback: CallbackQuery):
    """Handle my account button."""
    try:
        logger.info(f"User {callback.from_user.id} requested account info")
        user = await get_or_create_user(callback.from_user.id)
        keyword_count = await count_user_keywords(callback.from_user.id)
        
        expiry_text = ""
        if user.expiry_date:
            expiry_text = f"\n• Hết hạn: {user.expiry_date.strftime('%d/%m/%Y')}"
        
        # Determine Plan Display
        plan_display = "🆓 FREE"
        if user.plan_type == PlanType.VIP:
            plan_display = "💎 VIP"
        elif user.plan_type == PlanType.BUSINESS:
            plan_display = "🏢 BUSINESS"
        
        created_at_str = user.created_at.strftime('%d/%m/%Y') if user.created_at else 'N/A'
        
        # Escape username for Markdown
        username = user.username or 'N/A'
        if username != 'N/A':
            username = escape_markdown(username)

        text = f"""
👤 **Thông tin tài khoản**

• ID: `{user.id}`
• Username: @{username}
• Gói: {plan_display}{expiry_text}
• Số từ khóa: {keyword_count}{'/' + str(FREE_MAX_KEYWORDS) if user.plan_type == PlanType.FREE else ''}
• Ngày tham gia: {created_at_str}
"""
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in callback_my_account: {e}", exc_info=True)
        await callback.answer("❌ Có lỗi xảy ra khi tải thông tin tài khoản.", show_alert=True)


# ============ FSM Handlers ============
@dp.message(AddKeywordState.waiting_for_keyword, F.text)
async def process_add_keyword(message: types.Message, state: FSMContext):
    """Process keyword input."""
    logger.info(f"Processing keyword from user {message.from_user.id}: {message.text}")
    
    raw_text = message.text.strip()
    
    if not raw_text:
        await message.answer("⚠️ Từ khóa không được để trống!")
        return
    
    # Split by comma or newline to support multiple keywords
    keywords = [k.strip() for k in re.split(r'[,\n]', raw_text) if k.strip()]
    
    if not keywords:
        await message.answer("⚠️ Không tìm thấy từ khóa hợp lệ!")
        return

    added_keywords = []
    failed_keywords = []

    # Add to database
    try:
        async with AsyncSessionLocal() as session:
            # Check user plan for limits
            result = await session.execute(select(User).where(User.id == message.from_user.id))
            user = result.scalar_one_or_none()
            
            # Count existing keywords
            result = await session.execute(select(func.count(FilterRule.id)).where(FilterRule.user_id == message.from_user.id))
            current_count = result.scalar() or 0
            
            for raw_keyword in keywords:
                # 1. Normalization: Lowercase & Strip
                keyword = raw_keyword.lower().strip()
                
                # 2. Remove special characters (Keep alphanumeric, spaces, and $)
                # This removes emojis and punctuation like .,!?- etc.
                keyword = re.sub(r'[^\w\s$]', '', keyword)
                
                if not keyword:
                    failed_keywords.append(f"{raw_keyword} (Không hợp lệ sau khi chuẩn hóa)")
                    continue

                # 3. Length Check
                # Rule: >= 3 chars. Exception: 2 chars allowed if it starts with $ (e.g. $op)
                # Since we stripped special chars, $op is 3 chars. op is 2 chars.
                # So simple check: len < 3 is invalid.
                if len(keyword) < 3:
                    failed_keywords.append(f"{keyword} (Quá ngắn, tối thiểu 3 ký tự. Ví dụ: btc, $op)")
                    continue
                
                if len(keyword) > 50:
                    failed_keywords.append(f"{keyword} (Quá dài, tối đa 50 ký tự)")
                    continue
                
                # 4. Blacklist Check
                if keyword in KEYWORD_BLACKLIST:
                    failed_keywords.append(f"{keyword} (Từ khóa bị chặn vì quá thông dụng)")
                    continue
                
                # 5. Must contain at least one alphanumeric character (prevent just "$$$")
                if not re.search(r'[a-zA-Z0-9]', keyword):
                    failed_keywords.append(f"{keyword} (Không hợp lệ, phải chứa chữ hoặc số)")
                    continue

                # Check limit for FREE users
                if user.plan_type == PlanType.FREE and current_count >= FREE_MAX_KEYWORDS:
                    failed_keywords.append(f"{keyword} (Đạt giới hạn gói FREE: tối đa {FREE_MAX_KEYWORDS} từ)")
                    continue

                # Check duplicate
                # Ideally we check DB, but for simplicity let's just try insert
                # Or check if exists
                exists = await session.execute(
                    select(FilterRule).where(
                        FilterRule.user_id == message.from_user.id,
                        FilterRule.keyword == keyword
                    )
                )
                if exists.scalar_one_or_none():
                    failed_keywords.append(f"{keyword} (Đã tồn tại)")
                    continue

                new_rule = FilterRule(
                    user_id=message.from_user.id,
                    keyword=keyword,
                    is_active=True
                )
                session.add(new_rule)
                added_keywords.append(keyword)
                current_count += 1
            
            await session.commit()
        
        await state.clear()
        
        msg = ""
        if added_keywords:
            msg += f"✅ Đã thêm {len(added_keywords)} từ khóa:\n" + "\n".join([f"- `{k}`" for k in added_keywords])
        
        if failed_keywords:
            msg += "\n\n⚠️ Không thể thêm:\n" + "\n".join([f"- {k}" for k in failed_keywords])
            
        await message.answer(
            msg,
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        logger.info(f"User {message.from_user.id} added keywords: {added_keywords}")
    except Exception as e:
        logger.error(f"Error adding keyword: {e}")
        await message.answer("❌ Có lỗi xảy ra. Vui lòng thử lại!")
        await state.clear()


# ============ Catch-all handler for debugging ============
@dp.message(F.text)
async def catch_all_message(message: types.Message, state: FSMContext):
    """Catch all text messages for debugging."""
    current_state = await state.get_state()
    logger.info(f"Catch-all: User {message.from_user.id} sent '{message.text}', state={current_state}")
    
    # If user is in waiting_for_keyword state but FSM didn't catch it
    if current_state == AddKeywordState.waiting_for_keyword.state:
        logger.info("Redirecting to add keyword handler...")
        await process_add_keyword(message, state)


# ============ Notification Worker ============
async def notification_worker():
    """Background task to send notifications to users."""
    redis = await get_redis()
    logger.info("Notification Worker started...")
    
    while True:
        try:
            result = await redis.brpop([QUEUE_NOTIFICATIONS, QUEUE_PAYMENT_NOTIFICATIONS], timeout=1)
            
            if result:
                queue_name, data = result
                notification = json.loads(data)
                
                if queue_name == QUEUE_PAYMENT_NOTIFICATIONS:
                    # Handle Payment Notification
                    user_id = notification.get("user_id")
                    amount = notification.get("amount", 0)
                    expiry_str = notification.get("expiry_date", "")
                    
                    try:
                        expiry_date = datetime.fromisoformat(expiry_str)
                        expiry_display = expiry_date.strftime("%d/%m/%Y")
                    except:
                        expiry_display = expiry_str

                    payment_text = f"""
✅ **Thanh toán thành công!**

Cảm ơn bạn đã nâng cấp tài khoản.
💰 Số tiền: {amount:,.0f} VND
📅 Hạn sử dụng: {expiry_display}

Chúc bạn săn kèo thành công! 🚀
"""
                    try:
                        await bot.send_message(user_id, payment_text, parse_mode="Markdown")
                        logger.info(f"Payment notification sent to {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to send payment notification to {user_id}: {e}")
                    
                    continue

                # Handle Template Report
                if notification.get("type") == "TEMPLATE_REPORT":
                    user_id = notification["user_id"]
                    message_text = notification["message"]
                    try:
                        await bot.send_message(user_id, message_text, parse_mode="Markdown")
                        logger.info(f"Template report sent to {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to send template report to {user_id}: {e}")
                    continue

                # Handle Keyword Match Notification (QUEUE_NOTIFICATIONS)
                user_id = notification["user_id"]
                msg_data = notification["message"]
                keyword = notification["matched_keyword"]
                
                # Format notification message
                chat_title = escape_markdown(msg_data.get("chat_title", "Unknown"))
                text = escape_markdown(msg_data.get("text", "")[:500])  # Truncate long messages
                message_link = msg_data.get("message_link", "")
                ai_analysis = notification.get("ai_analysis")
                
                # Safe keyword display (remove backticks to avoid breaking markdown code block)
                safe_keyword = keyword.replace("`", "")

                # Compact Design
                # 🔔 Chat Title | 🎯 Keyword
                # 
                # Content...
                # 
                # [Link]
                
                notification_text = f"🔔 *{chat_title}* | 🎯 `{safe_keyword}`\n\n"
                notification_text += f"{text}\n\n"
                
                if message_link:
                    notification_text += f"[👉 Xem tin nhắn gốc]({message_link})"

                if ai_analysis:
                    # Append AI analysis directly (formatted by AI Engine)
                    notification_text += f"\n\n{ai_analysis}"
                
                # 1. Send to User (DM)
                try:
                    await bot.send_message(user_id, notification_text, parse_mode="Markdown")
                    logger.debug(f"Notification sent to {user_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification to {user_id}: {e}")

                # 2. Forward to Business Targets
                try:
                    async with AsyncSessionLocal() as session:
                        # Get targets
                        result = await session.execute(
                            select(UserForwardingTarget).where(UserForwardingTarget.user_id == user_id)
                        )
                        targets = result.scalars().all()
                        
                        if targets:
                            for target in targets:
                                try:
                                    await bot.send_message(target.channel_id, notification_text, parse_mode="Markdown")
                                    logger.debug(f"Forwarded to channel {target.channel_id} for user {user_id}")
                                    await asyncio.sleep(0.5) # Prevent FloodWait
                                except Exception as e:
                                    logger.error(f"Failed to forward to channel {target.channel_id}: {e}")
                except Exception as e:
                    logger.error(f"Error processing forwarding targets for {user_id}: {e}")

                # Anti-Ban: Random sleep to mimic human behavior
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
        except Exception as e:
            logger.error(f"Notification worker error: {e}")
            await asyncio.sleep(1)


@dp.callback_query(F.data == "affiliate_info")
async def callback_affiliate_info(callback: CallbackQuery):
    """Show affiliate info via callback."""
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        balance = user.commission_balance if user else 0.0
        
    text = f"""
🤝 **Chương trình Affiliate (Tiếp thị liên kết)**

🔗 **Link giới thiệu của bạn:**
`{ref_link}`

💰 **Hoa hồng hiện tại:** {balance:,.0f} VND

🎁 **Cơ chế:**
- Nhận ngay **20%** giá trị đơn hàng khi người bạn giới thiệu nâng cấp VIP.
- Hoa hồng được cộng trực tiếp vào số dư.
    """
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "smart_templates")
async def callback_smart_templates(callback: CallbackQuery):
    """Handle Smart AI Templates button."""
    # Reuse the logic from cmd_templates in handlers/templates.py
    # Since we can't easily call the handler directly with a Message object from a CallbackQuery,
    # we'll import the logic or redirect.
    # Better approach: Call the handler function directly if it accepts Union[Message, CallbackQuery]
    # or just replicate the logic/call a shared function.
    
    # Let's import the handler function
    from src.bot.handlers.templates import cmd_templates
    
    # We need to pass a Message-like object or adapt the handler.
    # The handler expects a Message. Let's adapt it.
    await cmd_templates(callback.message, user_id=callback.from_user.id)
    await callback.answer()


@dp.callback_query(F.data == "settings_menu")
async def callback_settings_menu(callback: CallbackQuery):
    """Show settings menu."""
    user_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        quiet_start = user.quiet_start.strftime("%H:%M") if user.quiet_start else "Tắt"
        quiet_end = user.quiet_end.strftime("%H:%M") if user.quiet_end else "Tắt"
        
    text = f"""
⚙️ **Cài đặt (Quiet Mode)**

Chế độ im lặng giúp bạn tắt thông báo vào khung giờ nghỉ ngơi.

🕒 **Trạng thái hiện tại:**
• Bắt đầu: `{quiet_start}`
• Kết thúc: `{quiet_end}`

📝 **Hướng dẫn thay đổi:**
Gõ lệnh theo cú pháp:
`/settings <giờ_bắt_đầu> <giờ_kết_thúc>`

Ví dụ:
• `/settings 23 7` (Im lặng từ 23h đêm đến 7h sáng)
• `/settings off` (Tắt chế độ im lặng)
    """
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

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

    # Check webhook
    webhook_info = await bot.get_webhook_info()
    logger.info(f"Webhook info: {webhook_info}")
    await bot.delete_webhook(drop_pending_updates=False)
    
    # Start polling
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
