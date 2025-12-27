"""
Script để thêm source channels vào database.
Sử dụng Telethon để resolve username -> chat_id
"""
import asyncio
import sys
import os
import json
import random

sys.path.append(os.getcwd())

import socks
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.errors import UsernameNotOccupiedError, ChannelPrivateError, FloodWaitError
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import SourceConfig
from src.common.logger import get_logger
from src.common.config import settings

logger = get_logger("seed_sources")

# Danh sách channels cần thêm
# Format: (username, name, tags_list, priority)
SIGNAL_CHANNELS = [
    # Trading Signals - Quốc tế
    ("WhalePumpSignals", "Whale Pump Signals", ["SIGNAL"], 8),
    ("Cryptoballers", "Crypto Ballers", ["SIGNAL"], 7),
    ("CryptoSignalsOrg", "Crypto Signals Org", ["SIGNAL"], 7),
    ("WolfofTrading", "Wolf of Trading", ["SIGNAL"], 8),
    ("AltSignals", "Alt Signals", ["SIGNAL"], 7),
    ("FedRussianInsiders", "Fed Russian Insiders", ["SIGNAL"], 9),
    ("Hirn_Crypto", "Hirn Crypto", ["SIGNAL"], 8),
    ("cryptosignalalert", "Crypto Signal Alert", ["SIGNAL"], 7),
    
    # Trading Signals - Việt Nam
    ("TradeCoinVN", "TradeCoin VN", ["SIGNAL"], 9),
    ("SignalCryptoVietnam", "Signal Crypto Vietnam", ["SIGNAL"], 8),
    ("CryptoVietnamTraders", "Crypto Vietnam Traders", ["SIGNAL"], 7),
    
    # KOLs & Analysts
    ("CryptoCapoChannel", "Crypto Capo", ["SIGNAL", "KOLS"], 9),
    ("Pentosh1", "Pentoshi", ["SIGNAL", "KOLS"], 9),
    ("SmartContracter", "Smart Contracter", ["SIGNAL", "KOLS"], 8),
    ("CryptoGodJohn", "Crypto God John", ["SIGNAL", "KOLS"], 8),
    ("TheCryptoDog", "The Crypto Dog", ["SIGNAL", "KOLS"], 7),
    ("ColdBloodedShiller", "Cold Blooded Shiller", ["SIGNAL", "KOLS"], 8),
    ("Hsaka_", "Hsaka", ["SIGNAL", "KOLS"], 8),
    ("Bluntz_eth", "Bluntz", ["SIGNAL", "KOLS"], 8),
    
    # Premium Channels
    ("CryptoInnerCircle", "Crypto Inner Circle", ["SIGNAL"], 9),
    ("MarginCall", "Margin Call", ["SIGNAL"], 8),
    ("AltcoinDaily", "Altcoin Daily", ["SIGNAL"], 8),
    ("CryptoBanter", "Crypto Banter", ["SIGNAL"], 8),
    ("BinanceKillers", "Binance Killers", ["SIGNAL"], 9),
    ("FatPigSignals", "Fat Pig Signals", ["SIGNAL"], 8),
    ("WatcherGuru", "Watcher Guru", ["SIGNAL"], 8),
]

ONCHAIN_CHANNELS = [
    # Whale Alerts
    ("whale_alert_io", "Whale Alert", ["ONCHAIN", "WHALE"], 10),
    ("waboratory", "Waboratory", ["ONCHAIN", "WHALE"], 9),
    ("lookonchain", "Lookonchain", ["ONCHAIN"], 10),
    ("spotonchain", "Spot On Chain", ["ONCHAIN"], 9),
    
    # On-chain Analytics
    ("CryptoQuantAlerts", "CryptoQuant Alerts", ["ONCHAIN", "DATA"], 9),
    ("santaboratory", "Santiment", ["ONCHAIN", "DATA"], 8),
    ("glaboratory", "Glassnode", ["ONCHAIN", "DATA"], 9),
    ("naboratory", "Nansen Alerts", ["ONCHAIN", "DATA"], 9),
    ("deaboratory", "DeBank", ["ONCHAIN"], 7),
    
    # DeFi & DEX
    ("DeFiLlama", "DefiLlama", ["ONCHAIN", "DEFI"], 8),
    ("UniswapLabs", "Uniswap", ["ONCHAIN", "DEFI"], 8),
    ("aaboratory", "Aave", ["ONCHAIN", "DEFI"], 7),
    
    # Blockchain Explorers
    ("etherscan", "Etherscan", ["ONCHAIN"], 7),
    ("bscscan_com", "BscScan", ["ONCHAIN"], 7),
    
    # Smart Money Trackers
    ("SmartMoneyTracker", "Smart Money Tracker", ["ONCHAIN", "WHALE"], 8),
    ("BlockchainWhispers", "Blockchain Whispers", ["ONCHAIN"], 8),
    
    # CEX Flows
    ("CEXFlows", "CEX Flows", ["ONCHAIN", "DATA"], 8),
    ("ExchangeInflows", "Exchange Inflows", ["ONCHAIN"], 7),
]

NEWS_VIP_CHANNELS = [
    # Major News
    ("caboratory", "Cointelegraph", ["NEWS_VIP"], 10),
    ("CoinDesk", "CoinDesk", ["NEWS_VIP"], 10),
    ("TheBlock__", "The Block", ["NEWS_VIP"], 9),
    ("Decrypt_co", "Decrypt", ["NEWS_VIP"], 8),
    ("bitcoinmagazine", "Bitcoin Magazine", ["NEWS_VIP"], 8),
    
    # Data & Analytics
    ("CoinGecko", "CoinGecko", ["NEWS_VIP"], 9),
    ("CoinMarketCap", "CoinMarketCap", ["NEWS_VIP"], 9),
    
    # Exchange Announcements
    ("binaboratory", "Binance Announcements", ["NEWS_VIP", "LISTING"], 10),
    ("coinbase", "Coinbase", ["NEWS_VIP", "LISTING"], 9),
    ("BybitAnnouncements", "Bybit Announcements", ["NEWS_VIP", "LISTING"], 8),
    ("OKXAnnouncements", "OKX Announcements", ["NEWS_VIP", "LISTING"], 8),
    
    # Analysts & Influencers
    ("BenjaminCowen", "Benjamin Cowen", ["NEWS_VIP", "SIGNAL"], 9),
    ("intocryptoverse", "Into The Cryptoverse", ["NEWS_VIP"], 8),
]

LOWCAP_CHANNELS = [
    # Gem Hunters
    ("ICODrops", "ICO Drops", ["LOWCAP", "IDO"], 9),
    ("Coin98Analytics", "Coin98 Analytics", ["NARRATIVE", "AIRDROP"], 8),
    ("100xGems", "100x Gems", ["LOWCAP"], 8),
    ("MoonShotCalls", "MoonShot Calls", ["LOWCAP"], 7),
    ("GemHuntersClub", "Gem Hunters Club", ["LOWCAP"], 7),
    
    # Airdrops & IDOs
    ("AirdropOfficial", "Airdrop Official", ["AIRDROP", "GUIDE"], 8),
    ("EarndropIO", "Earndrop IO", ["AIRDROP"], 7),
    
    # VC & Fundraising
    ("MessariCrypto", "Messari", ["LOWCAP", "DATA"], 8),
    ("TheBlockRes", "The Block Research", ["LOWCAP"], 8),
]


async def resolve_and_insert(client: TelegramClient, channels_list: list):
    """Resolve usernames to chat_ids and insert into database"""
    
    async with AsyncSessionLocal() as session:
        for username, name, tags, priority in channels_list:
            try:
                # Check if already exists by name
                stmt = select(SourceConfig).where(SourceConfig.name == name)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    logger.info(f"⏭️  Skipping {name} - already exists (chat_id: {existing.chat_id})")
                    continue
                
                # Resolve username to entity
                try:
                    entity = await client.get_entity(username)
                    chat_id = entity.id
                    
                    # Convert to proper format (-100 prefix for channels/supergroups)
                    if hasattr(entity, 'broadcast') or hasattr(entity, 'megagroup'):
                        if chat_id > 0:
                            chat_id = -1000000000000 - chat_id
                        elif not str(chat_id).startswith('-100'):
                            chat_id = int(f"-100{abs(chat_id)}")
                    
                    # Also check by chat_id
                    stmt = select(SourceConfig).where(SourceConfig.chat_id == chat_id)
                    result = await session.execute(stmt)
                    existing_by_id = result.scalar_one_or_none()
                    
                    if existing_by_id:
                        logger.info(f"⏭️  Skipping {name} - chat_id {chat_id} already exists")
                        continue
                    
                    # Create new source config
                    new_source = SourceConfig(
                        chat_id=chat_id,
                        name=name,
                        tags=tags,
                        priority=priority,
                        is_active=True
                    )
                    session.add(new_source)
                    await session.commit()
                    
                    logger.info(f"✅ Added: {name} (chat_id: {chat_id}, tags: {tags})")
                    
                    # Random delay 40-60s to avoid FloodWait
                    delay = random.randint(40, 60)
                    logger.info(f"⏳ Waiting {delay}s before next request...")
                    await asyncio.sleep(delay)
                    
                except UsernameNotOccupiedError:
                    logger.warning(f"❌ Username not found: @{username}")
                except ChannelPrivateError:
                    logger.warning(f"🔒 Channel is private: @{username}")
                except Exception as e:
                    logger.error(f"❌ Error resolving @{username}: {e}")
                    
            except FloodWaitError as e:
                logger.warning(f"⏳ Flood wait: {e.seconds}s - sleeping...")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                logger.error(f"❌ Error processing {name}: {e}")
                await session.rollback()


async def main():
    """Main function"""
    logger.info("🚀 Starting source seeding...")
    
    # Detect environment
    is_windows = os.name == 'nt'
    
    if is_windows:
        # Windows: use 84389961241 with proxy
        session_name = "84389961241"
    else:
        # Linux VPS: use ingestor_session (84389961241 is corrupted on VPS)
        session_name = "ingestor_session"
    
    session_path = os.path.join(os.getcwd(), "sessions", session_name)
    
    if not os.path.exists(f"{session_path}.session"):
        logger.error(f"❌ Session file not found: {session_path}.session")
        return
    
    # Load proxy config (only for Windows with 84389961241)
    proxy = None
    if is_windows:
        proxies_file = os.path.join(os.getcwd(), "proxies.json")
        if os.path.exists(proxies_file):
            with open(proxies_file, 'r') as f:
                proxies = json.load(f)
                if session_name in proxies:
                    p = proxies[session_name]
                proxy = (
                    socks.SOCKS5,
                    p["hostname"],
                    p["port"],
                    True,
                    p["username"],
                    p["password"]
                )
                logger.info(f"🔐 Using proxy: {p['hostname']}:{p['port']}")
    
    logger.info(f"📱 Using session: {session_name}")
    
    # Create Telethon client with proxy
    client = TelegramClient(
        session_path,
        settings.API_ID,
        settings.API_HASH,
        proxy=proxy
    )
    
    try:
        await client.start()
        logger.info("📱 Connected to Telegram")
        
        # Process each category
        logger.info("\n📊 Processing SIGNAL channels...")
        await resolve_and_insert(client, SIGNAL_CHANNELS)
        
        logger.info("\n🔗 Processing ONCHAIN channels...")
        await resolve_and_insert(client, ONCHAIN_CHANNELS)
        
        logger.info("\n📰 Processing NEWS_VIP channels...")
        await resolve_and_insert(client, NEWS_VIP_CHANNELS)
        
        logger.info("\n💎 Processing LOWCAP channels...")
        await resolve_and_insert(client, LOWCAP_CHANNELS)
        
        logger.info("\n✅ Seeding completed!")
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
