import asyncio
import json
import logging
import os
import random
import glob
import re
from typing import List, Dict

from dotenv import load_dotenv
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserBannedInChannel
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Setup Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
PROXIES_FILE = os.path.join(BASE_DIR, "proxies.json")
CONFIG_FILE = os.path.join(BASE_DIR, "marketing_config.json")

# --- Global State ---
# Cache dùng chung cho TOÀN BỘ clients để tránh việc 5 bot cùng spam 1 nhóm
# Structure: {group_id: timestamp}
shared_replied_cache: Dict[int, float] = {} 
BASE_COOLDOWN = 1800 # 30 minutes
clients: List[Client] = []

# --- Load Config ---
def load_json(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

marketing_config = load_json(CONFIG_FILE)
proxies_config = load_json(PROXIES_FILE)
KEYWORDS = marketing_config.get("keywords", [])
STATIC_MESSAGES = marketing_config.get("static_messages", [])
AI_PROMPT = marketing_config.get("ai_prompt", "")

# --- AI Setup ---
API_KEY = os.getenv("GEMINI_API_KEY")
model = None
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    logger.warning("GEMINI_API_KEY missing. Using static messages only.")

# --- Helper Functions ---

def get_proxy_for_session(session_name: str):
    # Fix regex để bắt chính xác số điện thoại (bỏ qua các ký tự khác)
    match = re.search(r"(?:^|_)(\d+)(?:_|\.|$)", session_name)
    if match:
        phone = match.group(1)
        if phone in proxies_config:
            p = proxies_config[phone]
            return {
                "scheme": p["scheme"],
                "hostname": p["hostname"],
                "port": p["port"],
                "username": p.get("username"),
                "password": p.get("password")
            }
    return None

async def generate_reply_content():
    """
    Logic thông minh: 
    - 40% dùng AI (nếu có) để tạo nội dung mới lạ.
    - 60% dùng tin nhắn tĩnh (nhanh, an toàn, đỡ tốn quota).
    """
    use_ai = model and random.random() < 0.4
    
    if use_ai:
        try:
            # Thêm timeout để tránh treo bot nếu API lag
            response = await asyncio.wait_for(
                model.generate_content_async(AI_PROMPT), 
                timeout=10.0
            )
            if response.text:
                return response.text.strip()
        except asyncio.TimeoutError:
            logger.warning("AI Generation timed out, falling back to static.")
        except Exception as e:
            logger.error(f"AI Error: {e}")
    
    # Fallback hoặc Random choice
    if STATIC_MESSAGES:
        return random.choice(STATIC_MESSAGES)
    return "Inbox me for details!" # Default nếu config rỗng

# --- Main Logic ---

async def main():
    session_files = glob.glob(os.path.join(SESSIONS_DIR, "*.session"))
    marketing_sessions = [
        f for f in session_files 
        if "ingestor" not in os.path.basename(f) and "journal" not in f
    ]

    if not marketing_sessions:
        logger.error("No sessions found.")
        return

    logger.info(f"Found {len(marketing_sessions)} sessions.")

    for session_path in marketing_sessions:
        session_name = os.path.basename(session_path).replace(".session", "")
        proxy = get_proxy_for_session(session_name)
        
        client = Client(
            name=session_name,
            workdir=SESSIONS_DIR,
            proxy=proxy,
            sleep_threshold=30 # Tự động ngủ nếu dính FloodWait dưới 30s
        )
        
        # Filter: Group only, Text only, Not from Me, Not from Bots (tránh trigger bot khác)
        @client.on_message(filters.group & filters.text & ~filters.me & ~filters.bot)
        async def handle_message(c: Client, m: Message):
            try:
                chat_id = m.chat.id
                text = m.text.lower()

                # 1. Global Cooldown Check (Check bộ nhớ chung)
                now = asyncio.get_running_loop().time()
                last_reply = shared_replied_cache.get(chat_id, 0)
                
                # Thêm "Jitter" (độ lệch ngẫu nhiên) vào cooldown để tránh pattern máy móc
                # Ví dụ: 30 phút + random(0-5 phút)
                current_cooldown = BASE_COOLDOWN + random.uniform(0, 300)
                
                if now - last_reply < current_cooldown:
                    return

                # 2. Check Keywords
                if any(kw in text for kw in KEYWORDS):
                    
                    # === CRITICAL FIX: RACE CONDITION ===
                    # Double-check lock: Kiểm tra lại 1 lần nữa sau khi đã match keyword
                    # Vì có thể 1 bot khác vừa set cache trong mili-giây trước
                    if asyncio.get_running_loop().time() - shared_replied_cache.get(chat_id, 0) < current_cooldown:
                        return

                    # Update Cache NGAY LẬP TỨC để chặn các bot khác trong cùng group
                    shared_replied_cache[chat_id] = now
                    
                    logger.info(f"[{c.name}] Keyword detected in {m.chat.title}")

                    # 3. Safety Checks (Quan trọng)
                    # Không reply tin nhắn quá ngắn (ví dụ: "hi", "ok") dễ bị coi là spam vô duyên
                    if len(text) < 3: 
                        return
                    
                    # (Tùy chọn) Không reply nếu user là Admin (Cần gọi API, tốn time nên cân nhắc)
                    # member = await c.get_chat_member(chat_id, m.from_user.id)
                    # if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                    #     return

                    # 4. Human Behavior Simulation
                    # Đọc tin nhắn (Mark as read)
                    await c.read_chat_history(chat_id, m.id)
                    
                    # Delay ngẫu nhiên lâu hơn chút (5-12s)
                    await asyncio.sleep(random.uniform(5, 12))

                    # Typing action
                    await c.send_chat_action(chat_id, enums.ChatAction.TYPING)
                    await asyncio.sleep(random.uniform(2, 5))

                    # 5. Generate & Send
                    reply_text = await generate_reply_content()
                    
                    try:
                        await m.reply_text(reply_text, parse_mode=enums.ParseMode.MARKDOWN)
                        logger.info(f"[{c.name}] Replied success.")
                    except FloodWait as e:
                        logger.warning(f"FloodWait: Sleeping {e.value}s")
                        await asyncio.sleep(e.value)
                    except UserBannedInChannel:
                        logger.error(f"[{c.name}] Banned in group {chat_id}. Removing from list.")
                        # Logic để rời nhóm hoặc đánh dấu nhóm này vào blacklist (cần code thêm)
                    except Exception as e:
                        logger.error(f"Send failed: {e}")

            except Exception as e:
                # Log lỗi nhưng không crash bot
                pass

        clients.append(client)

    if not clients:
        return

    logger.info("Starting clients...")
    # Dùng compose để chạy mượt hơn thay vì gather đơn thuần nếu số lượng acc lớn
    await asyncio.gather(*[c.start() for c in clients])
    logger.info("Sniper is active.")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped.")
