import asyncio
import json
import logging
import os
import random
from typing import List, Set

from pyrogram import Client, enums
from pyrogram.errors import FloodWait, BadRequest, InviteHashExpired, UserAlreadyParticipant
from pyrogram.raw import functions

# --- Configuration ---
SESSION_NAME = "84389961241"  # Using the specific session found in workspace
SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")
PROXIES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "proxies.json")
HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scanned_history.json")

KEYWORDS = ['đầu tư', 'chứng khoán', 'crypto chat', 'tín hiệu coin', 'việc làm online',"Crypto Việt Nam","Cộng đồng Crypto","Cộng đồng Bitcoin","Cộng đồng Ethereum","Trade coin","Học đầu tư Crypto","Hội những người chơi Crypto","Chia sẻ kiến thức Crypto","Kênh tin tức Crypto","Phân tích kỹ thuật Crypto","Cộng đồng NFT Việt Nam","DeFi Việt Nam","Cộng đồng Blockchain Việt Nam","Crypto Signals Việt Nam","Crypto Trading Việt Nam","Crypto Alerts Việt Nam","Crypto Tips Việt Nam","Crypto News Việt Nam","Crypto Discussion Việt Nam","Crypto Analysis Việt Nam","Crypto Education Việt Nam","Crypto Community Việt Nam","Crypto Investors Việt Nam","Crypto Enthusiasts Việt Nam","Crypto Traders Việt Nam","Crypto Mining Việt Nam","Crypto Projects Việt Nam","Crypto Startups Việt Nam","Crypto Developers Việt Nam","Crypto Entrepreneurs Việt Nam","Crypto Influencers Việt Nam","Crypto Bloggers Việt Nam","Crypto YouTubers Việt Nam","Crypto Podcasters Việt Nam","Crypto Events Việt Nam","Crypto Meetups Việt Nam","Crypto Workshops Việt Nam","Crypto Conferences Việt Nam"]

MIN_MEMBERS = 500
MAX_MEMBERS = 1000000
MAX_JOINS_PER_RUN = 5

# Setup Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("ScannerJoiner")

class HistoryManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.scanned_ids: Set[int] = self._load_history()

    def _load_history(self) -> Set[int]:
        if not os.path.exists(self.filepath):
            return set()
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get("scanned_ids", []))
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return set()

    def add(self, chat_id: int):
        self.scanned_ids.add(chat_id)
        self._save_history()

    def exists(self, chat_id: int) -> bool:
        return chat_id in self.scanned_ids

    def _save_history(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump({"scanned_ids": list(self.scanned_ids)}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

def load_proxy(session_name: str):
    """Load proxy config for the specific session."""
    if not os.path.exists(PROXIES_FILE):
        return None
    
    try:
        with open(PROXIES_FILE, 'r', encoding='utf-8') as f:
            proxies = json.load(f)
            # Extract phone number from session name (assuming session name is phone number)
            # or just try to match keys
            if session_name in proxies:
                p = proxies[session_name]
                return {
                    "scheme": p["scheme"],
                    "hostname": p["hostname"],
                    "port": p["port"],
                    "username": p.get("username"),
                    "password": p.get("password")
                }
    except Exception as e:
        logger.error(f"Error loading proxy: {e}")
    return None

async def main():
    # 1. Setup Client
    session_path = os.path.join(SESSIONS_DIR, SESSION_NAME)
    proxy_config = load_proxy(SESSION_NAME)
    
    logger.info(f"Initializing client for {SESSION_NAME}...")
    if proxy_config:
        logger.info(f"Using Proxy: {proxy_config['hostname']}:{proxy_config['port']}")

    app = Client(
        name=session_path,
        proxy=proxy_config,
        workdir=SESSIONS_DIR
    )

    history = HistoryManager(HISTORY_FILE)
    joins_count = 0

    async with app:
        logger.info("Client started successfully.")
        
        for keyword in KEYWORDS:
            if joins_count >= MAX_JOINS_PER_RUN:
                logger.warning("Reached MAX_JOINS_PER_RUN. Stopping.")
                break

            logger.info(f"🔎 Searching for keyword: '{keyword}'")
            
            try:
                # 2. Search Logic (Raw Function)
                # contacts.Search returns a contacts.Found object containing chats and users
                results = await app.invoke(
                    functions.contacts.Search(
                        q=keyword,
                        limit=20
                    )
                )
                
                if not results.chats:
                    logger.info(f"No results found for '{keyword}'")
                    continue

                logger.info(f"Found {len(results.chats)} potential candidates.")

                for chat_raw in results.chats:
                    if joins_count >= MAX_JOINS_PER_RUN:
                        break

                    chat_id = chat_raw.id
                    # Pyrogram raw chat IDs are positive integers. 
                    # When using high-level methods, we might need to convert or use username.
                    # However, raw objects usually have 'username'.
                    
                    username = getattr(chat_raw, 'username', None)
                    title = getattr(chat_raw, 'title', 'Unknown')
                    
                    # Filter 1: Must be Group or Supergroup (Channel/Chat)
                    # In raw API: 
                    # - Chat (legacy group)
                    # - Channel (supergroup or broadcast)
                    
                    is_broadcast = getattr(chat_raw, 'broadcast', False)
                    if is_broadcast:
                        logger.info(f"Skipping {title} (Broadcast Channel)")
                        continue

                    # Filter 2: History Check
                    # Note: Raw ID might need -100 prefix for high level, but for history we just store the raw ID to be consistent
                    if history.exists(chat_id):
                        logger.info(f"Skipping {title} (Already scanned)")
                        continue
                    
                    # Mark as scanned immediately to avoid re-processing in same run
                    history.add(chat_id)

                    if not username:
                        logger.info(f"Skipping {title} (No username, cannot join easily)")
                        continue

                    # 3. Filter & Join Logic
                    try:
                        # Get full chat details to check member count
                        # Using high-level get_chat for convenience
                        full_chat = await app.get_chat(username)
                        
                        member_count = full_chat.members_count
                        logger.info(f"Analyzing: {title} (@{username}) | Members: {member_count}")

                        if not (MIN_MEMBERS <= member_count <= MAX_MEMBERS):
                            logger.info(f"Skipping {title}: Member count {member_count} out of range [{MIN_MEMBERS}-{MAX_MEMBERS}]")
                            continue

                        # JOIN
                        logger.info(f"🚀 Attempting to join: {title}...")
                        await app.join_chat(username)
                        
                        # 4. Post-Join Checks
                        # Re-fetch chat to get updated permissions relative to 'me'
                        joined_chat = await app.get_chat(username)
                        permissions = joined_chat.permissions
                        
                        can_send = True
                        if permissions:
                            can_send = permissions.can_send_messages

                        if not can_send:
                            logger.warning(f"❌ Joined {title} but CANNOT send messages. Leaving...")
                            await app.leave_chat(joined_chat.id)
                        else:
                            logger.info(f"✅ Successfully joined and verified write access: {title}")
                            joins_count += 1
                            
                            # 5. Safety Sleep
                            sleep_time = random.randint(30, 60)
                            logger.info(f"Sleeping {sleep_time}s for safety...")
                            await asyncio.sleep(sleep_time)

                    except FloodWait as e:
                        logger.error(f"⚠️ FloodWait detected! Sleeping for {e.value} seconds.")
                        await asyncio.sleep(e.value)
                    except UserAlreadyParticipant:
                        logger.info(f"Already in {title}.")
                    except Exception as e:
                        logger.error(f"Error processing {title}: {e}")

            except FloodWait as e:
                logger.error(f"⚠️ FloodWait during search! Sleeping for {e.value} seconds.")
                await asyncio.sleep(e.value)
            except Exception as e:
                logger.error(f"Search error for '{keyword}': {e}")
            
            # Small delay between keywords
            await asyncio.sleep(5)

    logger.info("Scanner finished.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
