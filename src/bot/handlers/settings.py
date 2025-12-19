from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from sqlalchemy import select
from datetime import time
from src.database.db import AsyncSessionLocal
from src.database.models import User

router = Router()

@router.message(Command("settings"))
async def cmd_settings(message: types.Message, command: CommandObject):
    """
    Configure Quiet Mode.
    Usage: /settings <start_hour> <end_hour>
    Example: /settings 23 7 (Quiet from 23:00 to 07:00)
    To disable: /settings off
    """
    args = command.args
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.reply("⚠️ Vui lòng /start để đăng ký trước.")
            return

        if not args:
            # Show current settings
            start = user.quiet_start.strftime("%H:%M") if user.quiet_start else "Chưa đặt"
            end = user.quiet_end.strftime("%H:%M") if user.quiet_end else "Chưa đặt"
            
            msg = (
                "⚙️ **Cài đặt hiện tại**\n\n"
                f"🌙 **Giờ ngủ đông (Quiet Mode):** {start} - {end}\n\n"
                "Để cài đặt, dùng lệnh:\n"
                "`/settings 23 7` (Ngủ từ 23h đến 7h sáng)\n"
                "`/settings off` (Tắt chế độ ngủ)"
            )
            await message.reply(msg, parse_mode="Markdown")
            return

        if args.lower() == "off":
            user.quiet_start = None
            user.quiet_end = None
            await session.commit()
            await message.reply("✅ Đã tắt chế độ ngủ đông. Bạn sẽ nhận thông báo 24/7.")
            return

        try:
            parts = args.split()
            if len(parts) != 2:
                raise ValueError("Sai định dạng")
            
            start_hour = int(parts[0])
            end_hour = int(parts[1])
            
            if not (0 <= start_hour <= 23) or not (0 <= end_hour <= 23):
                await message.reply("⚠️ Giờ phải từ 0 đến 23.")
                return
            
            user.quiet_start = time(hour=start_hour, minute=0)
            user.quiet_end = time(hour=end_hour, minute=0)
            
            await session.commit()
            await message.reply(f"✅ Đã cài đặt giờ ngủ: **{start_hour}:00** đến **{end_hour}:00**.\nBot sẽ không gửi tin nhắn trong khoảng thời gian này.", parse_mode="Markdown")
            
        except ValueError:
            await message.reply("⚠️ Sai cú pháp!\nVí dụ: `/settings 23 7`", parse_mode="Markdown")
