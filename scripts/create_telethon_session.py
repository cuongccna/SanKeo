#!/usr/bin/env python3
"""
Tạo Telethon session cho ingestor
"""
import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

if not API_ID or not API_HASH:
    print("❌ API_ID/API_HASH chưa được set trong .env")
    exit(1)

# Ensure sessions directory exists
if not os.path.exists("sessions"):
    os.makedirs("sessions")

phone_number = input("Nhập số điện thoại (ví dụ: +84389961241): ").strip()
session_name = phone_number.replace("+", "")
session_path = f"sessions/{session_name}"

print(f"\n📱 Đang tạo Telethon session cho {phone_number}...")
print(f"📁 Session sẽ được lưu tại: {session_path}.session")

client = TelegramClient(session_path, API_ID, API_HASH)

async def create_session():
    try:
        await client.connect()
        
        # Check if already logged in
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"✅ Tài khoản đã được xác thực: {me.first_name} ({me.username})")
            return session_name
        
        # Need to log in
        print("\nĐang gửi mã OTP tới Telegram...")
        await client.send_code_request(phone_number)
        
        code = input("Nhập mã OTP: ").strip()
        
        try:
            await client.sign_in(phone_number, code)
        except Exception as e:
            print(f"❌ Lỗi đăng nhập: {e}")
            return None
        
        me = await client.get_me()
        print(f"✅ Đăng nhập thành công: {me.first_name} (@{me.username})")
        return session_name
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return None
    finally:
        await client.disconnect()

# Run async function
result = asyncio.run(create_session())

if result:
    print(f"\n🎉 Session '{result}' được tạo thành công!")
    print(f"📝 Để dùng session này, cập nhật trong ingestor:")
    print(f"   SESSION_NAME = 'sessions/{result}'")
else:
    print("\n❌ Không thể tạo session")
    exit(1)
