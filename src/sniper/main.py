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
replied_cache: Dict[int, float] = {}  # {group_id: timestamp}
COOLDOWN_SECONDS = 1800  # 30 minutes
clients: List[Client] = []

# --- Load Config ---
def load_json(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

marketing_config = load_json(CONFIG_FILE)
proxies_config = load_json(PROXIES_FILE)
KEYWORDS = marketing_config.get("keywords", [])
STATIC_MESSAGES = marketing_config.get("static_messages", [])
AI_PROMPT = marketing_config.get("ai_prompt", "")

# --- AI Setup ---
# Try to load API Key from env or config
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None
    logger.warning("GEMINI_API_KEY not found. AI generation will be disabled, using static messages only.")

# --- Helper Functions ---

def get_proxy_for_session(session_name: str):
    """
    Extract phone number from session name and find matching proxy.
    Session name format expected: '84912345678.session' or similar.
    """
    # Simple regex to find the phone number part
    match = re.search(r"(\d+)", session_name)
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

async def get_ai_reply():
    """Generate a reply using Gemini AI."""
    if not model:
        return random.choice(STATIC_MESSAGES)
    
    try:
        response = await model.generate_content_async(AI_PROMPT)
        if response.text:
            return response.text.strip()
    except Exception as e:
        logger.error(f"AI Generation failed: {e}")
    
    # Fallback
    return random.choice(STATIC_MESSAGES)

def get_random_message():
    """
    Returns a message either from AI (simulated/real) or Static list.
    For stability and speed, we mix them or prefer static if AI is slow.
    """
    # 30% chance to try AI generation if available, else use static
    # This keeps it fast but occasionally fresh.
    if model and random.random() < 0.3:
        # We can't await here easily without making this async, 
        # so for now let's stick to the async handler calling the async AI function.
        pass 
    return random.choice(STATIC_MESSAGES)

# --- Main Logic ---

async def main():
    # 1. Find Session Files
    session_files = glob.glob(os.path.join(SESSIONS_DIR, "*.session"))
    
    # Filter out ingestor and non-marketing sessions
    # Assuming any session NOT named 'ingestor_session' is a marketing session
    marketing_sessions = [
        f for f in session_files 
        if "ingestor_session" not in os.path.basename(f) 
        and "journal" not in f
    ]

    if not marketing_sessions:
        logger.error("No marketing sessions found in sessions/ directory.")
        return

    logger.info(f"Found {len(marketing_sessions)} marketing sessions: {[os.path.basename(f) for f in marketing_sessions]}")

    # 2. Initialize Clients
    for session_path in marketing_sessions:
        session_name = os.path.basename(session_path).replace(".session", "")
        
        # Determine Proxy
        proxy = get_proxy_for_session(session_name)
        
        client = Client(
            name=session_name,
            workdir=SESSIONS_DIR,
            proxy=proxy
        )
        
        # Attach Event Handler
        @client.on_message(filters.group & filters.text & ~filters.me)
        async def handle_message(c: Client, m: Message):
            try:
                chat_id = m.chat.id
                text = m.text.lower()

                # 1. Check Rate Limit (Global per group)
                now = asyncio.get_running_loop().time()
                last_reply = replied_cache.get(chat_id, 0)
                
                if now - last_reply < COOLDOWN_SECONDS:
                    return # Still in cooldown

                # 2. Check Keywords
                if any(kw in text for kw in KEYWORDS):
                    
                    # Update Rate Limit IMMEDIATELY to prevent race conditions from other bots
                    replied_cache[chat_id] = now
                    
                    logger.info(f"[{c.name}] Detected keyword in {m.chat.title} ({chat_id})")

                    # 3. Random Delay (Human Simulation)
                    delay = random.uniform(3, 8)
                    await asyncio.sleep(delay)

                    # 4. Send Typing Action
                    await c.send_chat_action(chat_id, enums.ChatAction.TYPING)
                    # Simulate typing time based on message length (approx)
                    await asyncio.sleep(random.uniform(1, 3))

                    # 5. Generate Content
                    # Try AI first, fallback to static
                    reply_text = await get_ai_reply()

                    # 6. Reply
                    await m.reply_text(reply_text, parse_mode=enums.ParseMode.MARKDOWN)
                    
                    logger.info(f"[{c.name}] Replied to user {m.from_user.id} in {m.chat.title}: '{reply_text}'")

            except Exception as e:
                logger.error(f"Error in handler: {e}")

        clients.append(client)

    # 3. Run Clients
    if not clients:
        logger.error("No clients initialized.")
        return

    logger.info("Starting all marketing clients...")
    await asyncio.gather(*[c.start() for c in clients])
    
    # Keep running
    logger.info("Sniper module is running. Press Ctrl+C to stop.")
    await asyncio.Event().wait()

    # Cleanup (Optional, usually handled by OS on force kill)
    for c in clients:
        await c.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sniper stopped by user.")
