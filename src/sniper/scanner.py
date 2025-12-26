import asyncio
import json
import logging
import os
import random
from typing import Set

from pyrogram import Client
from pyrogram.errors import FloodWait, UserAlreadyParticipant
from pyrogram.raw import functions
from pyrogram.raw.types import Channel, Chat

logger = logging.getLogger("SniperScanner")

# Config
KEYWORDS = ['Crypto','đầu tư', 'chứng khoán', 'crypto chat', 'tín hiệu coin', 'Crypto Việt Nam','Cộng đồng Crypto','Cộng đồng Bitcoin','Cộng đồng Ethereum','Trade coin','Học đầu tư Crypto','Hội những người chơi Crypto','Chia sẻ kiến thức Crypto','Kênh tin tức Crypto','Phân tích kỹ thuật Crypto','Cộng đồng NFT Việt Nam','DeFi Việt Nam','Cộng đồng Blockchain Việt Nam','Crypto Signals Việt Nam','Crypto Trading Việt Nam','Crypto Alerts Việt Nam','Crypto Tips Việt Nam','Crypto News Việt Nam','Crypto Discussion Việt Nam','Crypto Analysis Việt Nam','Crypto Education Việt Nam','Crypto Community Việt Nam','Crypto Investors Việt Nam','Crypto Enthusiasts Việt Nam','Crypto Traders Việt Nam','Crypto Mining Việt Nam','Crypto Projects Việt Nam','Crypto Startups Việt Nam','Crypto Developers Việt Nam','Crypto Entrepreneurs Việt Nam','Crypto Influencers Việt Nam','Crypto Bloggers Việt Nam','Crypto YouTubers Việt Nam','Crypto Podcasters Việt Nam','Crypto Events Việt Nam','Crypto Meetups Việt Nam','Crypto Workshops Việt Nam','Crypto Conferences Việt Nam']

MIN_MEMBERS = 500
MAX_MEMBERS = 1000000
MAX_JOINS_PER_RUN = 3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HISTORY_FILE = os.path.join(BASE_DIR, "scanned_history.json")

# --- GLOBAL LOCK CHO FILE I/O ---
file_lock = asyncio.Lock()

class HistoryManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.scanned_ids: Set[int] = set()

    async def load(self):
        """Load async để tránh chặn luồng chính"""
        if not os.path.exists(self.filepath):
            return
        async with file_lock:
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.scanned_ids = set(data.get("scanned_ids", []))
            except Exception as e:
                logger.error(f"Failed to load history: {e}")

    async def add(self, chat_id: int):
        self.scanned_ids.add(chat_id)
        await self._save()
    
    def exists(self, chat_id: int) -> bool:
        return chat_id in self.scanned_ids

    async def _save(self):
        async with file_lock:
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    json.dump({"scanned_ids": list(self.scanned_ids)}, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save history: {e}")

# Khởi tạo Global History Manager
history_manager = HistoryManager(HISTORY_FILE)

async def run_scanner_cycle(client: Client):
    """Runs one cycle of scanning and joining."""
    # Đảm bảo history đã load
    if not history_manager.scanned_ids:
        await history_manager.load()

    logger.info(f"[{client.name}] Starting scanner cycle...")
    joins_count = 0
    
    current_keywords = list(KEYWORDS)
    random.shuffle(current_keywords)

    # Chỉ scan tối đa 5 từ khóa mỗi lần chạy để tránh spam search API
    for keyword in current_keywords[:5]: 
        if joins_count >= MAX_JOINS_PER_RUN:
            break

        logger.info(f"🔎 Searching: '{keyword}'")
        
        try:
            # Gọi API Search
            results = await client.invoke(
                functions.contacts.Search(
                    q=keyword,
                    limit=20
                )
            )
            
            if not results.chats:
                await asyncio.sleep(random.uniform(5, 10)) # Nghỉ giữa các keywords
                continue

            for chat_raw in results.chats:
                if joins_count >= MAX_JOINS_PER_RUN:
                    break

                # Lấy ID và check History
                chat_id = chat_raw.id
                # Telegram raw ID thường dương, nhưng pyrogram dùng ID âm (-100...) cho channel/group
                # Chúng ta sẽ lưu raw ID để đơn giản hóa việc check
                
                if history_manager.exists(chat_id):
                    continue
                
                # Đánh dấu đã scan để lần sau không check lại (dù join hay không)
                await history_manager.add(chat_id)

                title = getattr(chat_raw, 'title', 'Unknown')
                username = getattr(chat_raw, 'username', None)

                # Filter: Chỉ lấy Channel hoặc Chat (Group)
                if not isinstance(chat_raw, (Channel, Chat)):
                    continue

                # Filter: Bỏ qua Broadcast Channels (Chỉ join Group/Supergroup)
                # Channel object có thuộc tính 'broadcast' = True nếu là kênh thông báo
                if isinstance(chat_raw, Channel) and getattr(chat_raw, 'broadcast', False):
                    continue

                if not username:
                    continue

                # === TỐI ƯU HÓA: KHÔNG GỌI client.get_chat() ===
                # Dữ liệu participants_count thường có sẵn trong kết quả search
                member_count = getattr(chat_raw, 'participants_count', 0)
                
                # Nếu member_count = 0 (do API không trả về), lúc này mới cực chẳng đã gọi get_chat
                # Hoặc chấp nhận bỏ qua để an toàn
                if member_count == 0:
                     # logger.debug(f"Skipping {title}: No member count info")
                     # continue
                     pass # Có thể bỏ qua check này nếu muốn mạo hiểm hơn

                if member_count > 0 and not (MIN_MEMBERS <= member_count <= MAX_MEMBERS):
                    continue

                logger.info(f"🚀 Attempting join: {title} (@{username}) - {member_count} mems")
                
                try:
                    await client.join_chat(username)
                    
                    # Check quyền gửi tin nhắn sau khi join
                    # Lúc này mới cần gọi get_chat vì đã là member
                    joined_chat = await client.get_chat(username)
                    
                    can_send = joined_chat.permissions.can_send_messages if joined_chat.permissions else True
                    
                    if not can_send:
                        logger.warning(f"❌ Joined {title} but READ-ONLY. Leaving...")
                        await client.leave_chat(joined_chat.id)
                    else:
                        logger.info(f"✅ JOINED SUCCESS: {title}")
                        joins_count += 1
                        # Nghỉ dài sau khi join thành công
                        await asyncio.sleep(random.randint(45, 90))

                except FloodWait as e:
                    logger.warning(f"FloodWait: {e.value}s. Stopping cycle.")
                    return # Dừng luôn cycle này nếu dính floodwait
                except UserAlreadyParticipant:
                    logger.info(f"Already in {title}")
                except Exception as e:
                    logger.error(f"Join error {title}: {e}")

        except Exception as e:
            logger.error(f"Search error: {e}")
        
        # Nghỉ giữa các lần search keyword
        await asyncio.sleep(random.uniform(10, 20))

    logger.info(f"[{client.name}] Cycle finished. Joined {joins_count}.")
