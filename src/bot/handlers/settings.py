from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject, ChatMemberUpdatedFilter, KICKED, LEFT, RESTRICTED, MEMBER, ADMINISTRATOR, CREATOR
from aiogram.types import ChatMemberUpdated
from sqlalchemy import select, delete
from datetime import time
from src.database.db import AsyncSessionLocal
from src.database.models import User, UserForwardingTarget, PlanType

router = Router()

@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated):
    """
    Handle when bot is added to a channel/group.
    """
    # Only care if bot is added as admin or member (if group allows)
    # Usually for channels, bot must be admin to post.
    new_state = event.new_chat_member.status
    
    # If bot is kicked or left, remove target
    if new_state in ["kicked", "left"]:
        chat = event.chat
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(UserForwardingTarget).where(UserForwardingTarget.channel_id == chat.id)
            )
            await session.commit()
        return

    # If bot is added (member or admin)
    if new_state in ["member", "administrator", "creator"]:
        user = event.from_user
        chat = event.chat
        
        # Ignore private chats
        if chat.type == "private":
            return

        async with AsyncSessionLocal() as session:
            # Check user plan
            db_user = await session.get(User, user.id)
            if not db_user:
                # User not registered
                await event.bot.leave_chat(chat.id)
                try:
                    await event.bot.send_message(user.id, "⚠️ Bạn chưa đăng ký sử dụng Bot. Vui lòng /start trước.")
                except:
                    pass
                return

            # Check if Business Plan
            if db_user.plan_type != PlanType.BUSINESS:
                 await event.bot.leave_chat(chat.id)
                 try:
                    await event.bot.send_message(user.id, "⚠️ Tính năng tự động forward tin nhắn vào nhóm riêng chỉ dành cho gói **Business**.\nVui lòng nâng cấp để sử dụng.", parse_mode="Markdown")
                 except:
                    pass
                 return
            
            # Save target
            # Check if already exists
            existing = await session.execute(
                select(UserForwardingTarget).where(
                    UserForwardingTarget.user_id == user.id,
                    UserForwardingTarget.channel_id == chat.id
                )
            )
            if existing.scalar_one_or_none():
                # Update title if changed
                # But for now just return
                return

            new_target = UserForwardingTarget(
                user_id=user.id,
                channel_id=chat.id,
                title=chat.title
            )
            session.add(new_target)
            await session.commit()
            
            try:
                await event.bot.send_message(chat.id, "✅ Bot đã được kết nối thành công! Tin nhắn lọc được sẽ được chuyển tiếp vào đây.")
                await event.bot.send_message(user.id, f"✅ Đã kết nối thành công với nhóm **{chat.title}**!")
            except:
                pass

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
