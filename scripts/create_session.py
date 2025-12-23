import os
from dotenv import load_dotenv
from pyrogram import Client

# Load env to get default API_ID/HASH if available
load_dotenv()

# Ensure sessions directory exists
if not os.path.exists("sessions"):
    os.makedirs("sessions")

print("--- Telegram Session Creator ---")
print("Script này giúp bạn tạo file session cho tài khoản Marketing.")

# Get credentials
# Ưu tiên lấy từ biến môi trường, nếu không có thì nhập tay
env_api_id = os.getenv("API_ID")
env_api_hash = os.getenv("API_HASH")

if env_api_id and env_api_hash:
    print(f"Đã tìm thấy API ID/HASH trong .env: {env_api_id} / ******")
    use_env = input("Bạn có muốn dùng API ID/HASH này không? (y/n): ").lower()
    if use_env == 'y':
        api_id = env_api_id
        api_hash = env_api_hash
    else:
        api_id = input("Nhập API ID: ")
        api_hash = input("Nhập API HASH: ")
else:
    api_id = input("Nhập API ID: ")
    api_hash = input("Nhập API HASH: ")

phone_number = input("Nhập số điện thoại (định dạng 84xxxxxxxxx): ")

# Clean phone number for filename
session_name = phone_number.strip().replace("+", "")

app = Client(
    name=session_name,
    api_id=api_id,
    api_hash=api_hash,
    workdir="sessions/",
    phone_number=phone_number
)

print(f"\nĐang kết nối tới Telegram cho số {phone_number}...")
print("Vui lòng nhập mã OTP khi được yêu cầu.")

try:
    with app:
        me = app.get_me()
        print(f"\n✅ Tạo session thành công cho user: {me.first_name} (@{me.username})")
        print(f"📁 File session đã được lưu tại: sessions/{session_name}.session")
except Exception as e:
    print(f"\n❌ Có lỗi xảy ra: {e}")
