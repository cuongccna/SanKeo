import asyncio
import json
import logging
import os
import random
from typing import Set, List

from pyrogram import Client
from pyrogram.errors import FloodWait, UserAlreadyParticipant
from pyrogram.raw import functions

logger = logging.getLogger("SniperScanner")

# Config
KEYWORDS = ['đầu tư', 'chứng khoán', 'crypto chat', 'tín hiệu coin', "Crypto Việt Nam","Cộng đồng Crypto","Cộng đồng Bitcoin","Cộng đồng Ethereum","Trade coin","Học đầu tư Crypto","Hội những người chơi Crypto","Chia sẻ kiến thức Crypto","Kênh tin tức Crypto","Phân tích kỹ thuật Crypto","Cộng đồng NFT Việt Nam","DeFi Việt Nam","Cộng đồng Blockchain Việt Nam","Crypto Signals Việt Nam","Crypto Trading Việt Nam","Crypto Alerts Việt Nam","Crypto Tips Việt Nam","Crypto News Việt Nam","Crypto Discussion Việt Nam","Crypto Analysis Việt Nam","Crypto Education Việt Nam","Crypto Community Việt Nam","Crypto Investors Việt Nam","Crypto Enthusiasts Việt Nam","Crypto Traders Việt Nam","Crypto Mining Việt Nam","Crypto Projects Việt Nam","Crypto Startups Việt Nam","Crypto Developers Việt Nam","Crypto Entrepreneurs Việt Nam","Crypto Influencers Việt Nam","Crypto Bloggers Việt Nam","Crypto YouTubers Việt Nam","Crypto Podcasters Việt Nam","Crypto Events Việt Nam","Crypto Meetups Việt Nam","Crypto Workshops Việt Nam","Crypto Conferences Việt Nam"]

MIN_MEMBERS = 500
MAX_MEMBERS = 1000000
MAX_JOINS_PER_RUN = 3 # Low limit to avoid spamming while running in background

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HISTORY_FILE = os.path.join(BASE_DIR, "scanned_history.json")

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

async def run_scanner_cycle(client: Client):
    """Runs one cycle of scanning and joining."""
    logger.info(f"[{client.name}] Starting scanner cycle...")
    history = HistoryManager(HISTORY_FILE)
    joins_count = 0
    
    # Shuffle keywords
    current_keywords = list(KEYWORDS)
    random.shuffle(current_keywords)

    for keyword in current_keywords:
        if joins_count >= MAX_JOINS_PER_RUN:
            logger.info("Reached MAX_JOINS_PER_RUN. Stopping scanner cycle.")
            break

        logger.info(f"🔎 Searching for keyword: '{keyword}'")
        
        try:
            results = await client.invoke(
                functions.contacts.Search(
                    q=keyword,
                    limit=20
                )
            )
            
            if not results.chats:
                continue

            for chat_raw in results.chats:
                if joins_count >= MAX_JOINS_PER_RUN:
                    break

                chat_id = chat_raw.id
                username = getattr(chat_raw, 'username', None)
                title = getattr(chat_raw, 'title', 'Unknown')
                
                is_broadcast = getattr(chat_raw, 'broadcast', False)
                if is_broadcast:
                    logger.info(f"Skipping {title}: Broadcast Channel")
                    continue

                if history.exists(chat_id):
                    logger.info(f"Skipping {title}: Already scanned")
                    continue
                
                history.add(chat_id)

                if not username:
                    logger.info(f"Skipping {title}: No username")
                    continue

                try:
                    full_chat = await client.get_chat(username)
                    member_count = full_chat.members_count
                    
                    if not (MIN_MEMBERS <= member_count <= MAX_MEMBERS):
                        logger.info(f"Skipping {title}: Members {member_count} not in range")
                        continue

                    logger.info(f"🚀 Attempting to join: {title} (@{username})")
                    await client.join_chat(username)
                    
                    # Post-join check
                    joined_chat = await client.get_chat(username)
                    permissions = joined_chat.permissions
                    can_send = True
                    if permissions:
                        can_send = permissions.can_send_messages

                    if not can_send:
                        logger.warning(f"❌ Joined {title} but CANNOT send messages. Leaving...")
                        await client.leave_chat(joined_chat.id)
                    else:
                        logger.info(f"✅ Successfully joined: {title}")
                        joins_count += 1
                        await asyncio.sleep(random.randint(30, 60))

                except FloodWait as e:
                    logger.warning(f"FloodWait: {e.value}s")
                    await asyncio.sleep(e.value)
                except UserAlreadyParticipant:
                    pass
                except Exception as e:
                    logger.error(f"Error joining {title}: {e}")

        except Exception as e:
            logger.error(f"Search error: {e}")
        
        await asyncio.sleep(5)

    logger.info(f"[{client.name}] Scanner cycle finished. Joined {joins_count} groups.")
