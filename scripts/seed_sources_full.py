"""
Script để thêm source channels vào database.
Sử dụng Telethon để resolve username -> chat_id
Danh sách đầy đủ 100+ channels cho mỗi tag chính
"""
import asyncio
import sys
import os
import json
import random

sys.path.append(os.getcwd())

import socks
from telethon import TelegramClient
from telethon.errors import UsernameNotOccupiedError, ChannelPrivateError, FloodWaitError
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import SourceConfig
from src.common.logger import get_logger
from src.common.config import settings

logger = get_logger("seed_sources_full")

# ==============================================================================
# TAG: ONCHAIN & WHALE - On-chain Analytics & Whale Tracking
# ==============================================================================
ONCHAIN_WHALE_CHANNELS = [
    # Whale Alerts - Top Tier
    ("whale_alert_io", "Whale Alert", ["ONCHAIN", "WHALE"], 10),
    ("lookonchain", "Lookonchain", ["ONCHAIN", "WHALE"], 10),
    ("spotonchain", "Spot On Chain", ["ONCHAIN", "WHALE"], 10),
    ("WhaleInsider", "Whale Insider", ["ONCHAIN", "WHALE"], 9),
    ("waboratory", "Whale Watcher", ["ONCHAIN", "WHALE"], 9),
    
    # On-chain Data Providers
    ("cryptaboratory", "CryptoQuant", ["ONCHAIN", "DATA"], 10),
    ("glaboratory", "Glassnode Alerts", ["ONCHAIN", "DATA"], 10),
    ("naboratory", "Nansen Alerts", ["ONCHAIN", "DATA"], 9),
    ("santaboratory", "Santiment", ["ONCHAIN", "DATA"], 9),
    ("IntoTheBlock", "IntoTheBlock", ["ONCHAIN", "DATA"], 9),
    ("Messari", "Messari", ["ONCHAIN", "DATA"], 9),
    ("TokenTerminal", "Token Terminal", ["ONCHAIN", "DATA"], 8),
    ("DuneAnalytics", "Dune Analytics", ["ONCHAIN", "DATA"], 8),
    
    # Smart Money Trackers
    ("SmartMoneyAlerts", "Smart Money Alerts", ["ONCHAIN", "WHALE"], 9),
    ("arkaboratory", "Arkham Intelligence", ["ONCHAIN", "WHALE"], 9),
    ("DeBank_Official", "DeBank", ["ONCHAIN", "WHALE"], 8),
    ("ZerionHQ", "Zerion", ["ONCHAIN"], 8),
    
    # Exchange Flow Trackers
    ("CexInflowOutflow", "CEX Flow Tracker", ["ONCHAIN", "DATA"], 9),
    ("BitcoinFlow", "Bitcoin Flow", ["ONCHAIN"], 8),
    ("EthereumFlow", "Ethereum Flow", ["ONCHAIN"], 8),
    
    # DeFi On-chain
    ("DeFiLlama", "DefiLlama", ["ONCHAIN", "DEFI"], 9),
    ("DefiPulse", "DeFi Pulse", ["ONCHAIN", "DEFI"], 8),
    ("LlamaAirdrop", "Llama Airdrops", ["ONCHAIN", "AIRDROP"], 8),
    
    # Blockchain Explorers
    ("etherscan", "Etherscan", ["ONCHAIN"], 8),
    ("BscScan", "BscScan", ["ONCHAIN"], 8),
    ("SolscanAlert", "Solscan Alerts", ["ONCHAIN"], 8),
    ("PolygonScan", "PolygonScan", ["ONCHAIN"], 7),
    ("ArbiscanAlert", "Arbiscan", ["ONCHAIN"], 7),
    
    # Additional Whale/On-chain
    ("CryptoWhaleBot", "Crypto Whale Bot", ["ONCHAIN", "WHALE"], 8),
    ("BTCWhaleAlert", "BTC Whale Alert", ["ONCHAIN", "WHALE"], 8),
    ("ETHWhaleWatch", "ETH Whale Watch", ["ONCHAIN", "WHALE"], 8),
    ("StablecoinFlow", "Stablecoin Flow", ["ONCHAIN", "DATA"], 8),
    ("USDTTracker", "USDT Tracker", ["ONCHAIN"], 7),
    ("USDCFlow", "USDC Flow", ["ONCHAIN"], 7),
]

# ==============================================================================
# TAG: SIGNAL & KOLS - Trading Signals & Key Opinion Leaders
# ==============================================================================
SIGNAL_KOLS_CHANNELS = [
    # Top Global KOLs
    ("CryptoCapo", "Crypto Capo", ["SIGNAL", "KOLS"], 10),
    ("Pentosh1Channel", "Pentoshi", ["SIGNAL", "KOLS"], 10),
    ("CryptoCred", "Crypto Cred", ["SIGNAL", "KOLS"], 10),
    ("trader1sz", "Trader SZ", ["SIGNAL", "KOLS"], 9),
    ("CryptoTony", "Crypto Tony", ["SIGNAL", "KOLS"], 9),
    ("CryptoMichNL", "Michaël van de Poppe", ["SIGNAL", "KOLS"], 10),
    ("AltcoinSherpa", "Altcoin Sherpa", ["SIGNAL", "KOLS"], 9),
    ("SmartContracter", "Smart Contracter", ["SIGNAL", "KOLS"], 9),
    ("CryptoDonAlt", "DonAlt", ["SIGNAL", "KOLS"], 9),
    ("Bluntz_eth", "Bluntz", ["SIGNAL", "KOLS"], 9),
    ("ColdBloodedShill", "Cold Blooded Shiller", ["SIGNAL", "KOLS"], 9),
    ("CryptoGodJohn", "Crypto God John", ["SIGNAL", "KOLS"], 8),
    ("TheCryptoZombie", "The Crypto Zombie", ["SIGNAL", "KOLS"], 8),
    ("CryptoJack", "Crypto Jack", ["SIGNAL", "KOLS"], 8),
    ("CryptoKaleo", "Kaleo", ["SIGNAL", "KOLS"], 9),
    ("HsakaTrades", "Hsaka", ["SIGNAL", "KOLS"], 9),
    ("CryptoBirb", "Crypto Birb", ["SIGNAL", "KOLS"], 8),
    ("CryptoRand", "Crypto Rand", ["SIGNAL", "KOLS"], 8),
    ("WhalePanda", "WhalePanda", ["SIGNAL", "KOLS"], 8),
    ("PeterLBrandt", "Peter Brandt", ["SIGNAL", "KOLS"], 9),
    
    # Premium Signal Groups
    ("CryptoInnerCircle", "Crypto Inner Circle", ["SIGNAL"], 10),
    ("BinanceKillers", "Binance Killers", ["SIGNAL"], 10),
    ("WolfofTrading", "Wolf of Trading", ["SIGNAL"], 9),
    ("FatPigSignals", "Fat Pig Signals", ["SIGNAL"], 9),
    ("AltSignals", "Alt Signals", ["SIGNAL"], 9),
    ("CryptoSignalsIO", "Crypto Signals IO", ["SIGNAL"], 8),
    ("FedRussianInsiders", "Fed Russian Insiders", ["SIGNAL"], 9),
    ("HirnCrypto", "Hirn Crypto", ["SIGNAL"], 8),
    ("MYCSignals", "MYC Signals", ["SIGNAL"], 8),
    ("RocketWallet", "Rocket Wallet", ["SIGNAL"], 8),
    ("CryptoQualitySignals", "Crypto Quality Signals", ["SIGNAL"], 8),
    ("CoinsiderSignals", "Coinsider Signals", ["SIGNAL"], 8),
    ("WatcherGuru", "Watcher Guru", ["SIGNAL", "NEWS_VIP"], 9),
    ("CryptoAlerts", "Crypto Alerts", ["SIGNAL"], 8),
    ("MarginCall", "Margin Call", ["SIGNAL"], 8),
    
    # Vietnam KOLs & Signals
    ("TradeCoinVietnam", "TradeCoin Vietnam", ["SIGNAL", "KOLS"], 9),
    ("CryptoVietnamTraders", "Crypto Vietnam Traders", ["SIGNAL"], 8),
    ("HCCapital", "HC Capital", ["SIGNAL", "LOWCAP"], 8),
    ("Coin98Analytics", "Coin98 Analytics", ["SIGNAL", "NARRATIVE"], 9),
    ("VNDCCrypto", "VNDC Crypto", ["SIGNAL"], 7),
    ("CryptoVietNam", "Crypto VietNam", ["SIGNAL"], 7),
    ("SignalCryptoVN", "Signal Crypto VN", ["SIGNAL"], 7),
    ("BitcoinVN", "Bitcoin Vietnam", ["SIGNAL"], 7),
    
    # TA & Analysis Channels
    ("TradingView", "TradingView", ["SIGNAL", "DATA"], 9),
    ("CryptoTA", "Crypto TA", ["SIGNAL"], 8),
    ("TechnicalRoundup", "Technical Roundup", ["SIGNAL"], 8),
    ("ChartChampions", "Chart Champions", ["SIGNAL"], 8),
]

# ==============================================================================
# TAG: NEWS_VIP & LISTING - Breaking News & Exchange Listings
# ==============================================================================
NEWS_LISTING_CHANNELS = [
    # Tier 1 News Sources
    ("Cointelegraph", "Cointelegraph", ["NEWS_VIP"], 10),
    ("CoinDesk", "CoinDesk", ["NEWS_VIP"], 10),
    ("TheBlock_", "The Block", ["NEWS_VIP"], 10),
    ("Decrypt_co", "Decrypt", ["NEWS_VIP"], 9),
    ("bitcoinmagazine", "Bitcoin Magazine", ["NEWS_VIP"], 9),
    ("CryptoSlate", "CryptoSlate", ["NEWS_VIP"], 8),
    ("NewsBTC", "NewsBTC", ["NEWS_VIP"], 8),
    ("Cryptonews", "Cryptonews", ["NEWS_VIP"], 8),
    ("DailyHodl", "The Daily Hodl", ["NEWS_VIP"], 8),
    ("BeInCrypto", "BeInCrypto", ["NEWS_VIP"], 8),
    ("CryptoNews", "Crypto News", ["NEWS_VIP"], 8),
    
    # Speed News (Fastest)
    ("TreeNewsInfo", "Tree News", ["NEWS_VIP", "SENTIMENT"], 10),
    ("WuBlockchain", "Wu Blockchain", ["NEWS_VIP"], 10),
    ("tier10k", "Tier10K", ["NEWS_VIP"], 9),
    ("CoinNess", "CoinNess", ["NEWS_VIP"], 9),
    ("BlockBeatsNews", "BlockBeats", ["NEWS_VIP"], 9),
    ("OdailyNews", "Odaily", ["NEWS_VIP"], 8),
    ("PANewsLab", "PANews", ["NEWS_VIP"], 8),
    ("ForesightNews", "Foresight News", ["NEWS_VIP"], 8),
    
    # Exchange Official Announcements
    ("BinanceAnnouncements", "Binance Announcements", ["LISTING", "NEWS_VIP"], 10),
    ("Coinbase", "Coinbase", ["LISTING", "NEWS_VIP"], 10),
    ("OKXAnnouncements", "OKX Announcements", ["LISTING", "NEWS_VIP"], 9),
    ("BybitAnnouncements", "Bybit Announcements", ["LISTING", "NEWS_VIP"], 9),
    ("KuCoinNews", "KuCoin News", ["LISTING", "NEWS_VIP"], 8),
    ("GateioAnnouncement", "Gate.io Announcement", ["LISTING", "NEWS_VIP"], 8),
    ("BitgetAnnouncement", "Bitget Announcement", ["LISTING", "NEWS_VIP"], 8),
    ("ABORATORY", "MEXC Announcement", ["LISTING"], 8),
    ("HTXGlobal", "HTX Global", ["LISTING"], 7),
    ("CryptoComOfficial", "Crypto.com Official", ["LISTING", "NEWS_VIP"], 8),
    ("KrakenExchange", "Kraken", ["LISTING", "NEWS_VIP"], 8),
    
    # Listing Trackers
    ("ListingWatch", "Listing Watch", ["LISTING"], 9),
    ("NewListings", "New Listings", ["LISTING"], 8),
    ("BinanceListingNews", "Binance Listing News", ["LISTING"], 8),
    ("CoinbaseListings", "Coinbase Listings", ["LISTING"], 8),
    ("LaunchpadNews", "Launchpad News", ["LISTING", "IDO"], 8),
    
    # Data & Analytics News
    ("CoinGecko", "CoinGecko", ["NEWS_VIP", "DATA"], 9),
    ("CoinMarketCap", "CoinMarketCap", ["NEWS_VIP", "DATA"], 9),
    ("CryptoCompare", "CryptoCompare", ["NEWS_VIP", "DATA"], 8),
    
    # Analyst Channels
    ("BenjaminCowen", "Benjamin Cowen", ["NEWS_VIP", "SIGNAL"], 9),
    ("CryptoverseJourney", "Into The Cryptoverse", ["NEWS_VIP", "SIGNAL"], 9),
    ("CoinBureau", "Coin Bureau", ["NEWS_VIP"], 9),
    ("MMCrypto", "MMCrypto", ["NEWS_VIP", "SIGNAL"], 8),
    ("CryptoZeus", "Crypto Zeus", ["NEWS_VIP"], 8),
]

# ==============================================================================
# TAG: LOWCAP & IDO - Low Cap Gems & IDO/Launchpad
# ==============================================================================
LOWCAP_IDO_CHANNELS = [
    # Gem Hunters
    ("GemHuntersClub", "Gem Hunters Club", ["LOWCAP"], 9),
    ("100xGems", "100x Gems", ["LOWCAP"], 9),
    ("LowcapGems", "Lowcap Gems", ["LOWCAP"], 8),
    ("CryptoGemsFinder", "Crypto Gems Finder", ["LOWCAP"], 8),
    ("MoonShotCalls", "MoonShot Calls", ["LOWCAP"], 8),
    ("GemHunterNews", "Gem Hunter News", ["LOWCAP"], 8),
    ("NextGem", "Next Gem", ["LOWCAP"], 8),
    ("CryptoMoonShots", "Crypto MoonShots", ["LOWCAP"], 8),
    ("AltGems", "Alt Gems", ["LOWCAP"], 8),
    ("HiddenGems", "Hidden Gems", ["LOWCAP"], 8),
    ("DegenGems", "Degen Gems", ["LOWCAP"], 7),
    ("GemAlerts", "Gem Alerts", ["LOWCAP"], 7),
    ("NewGemAlert", "New Gem Alert", ["LOWCAP"], 7),
    ("CryptoGemCall", "Crypto Gem Call", ["LOWCAP"], 7),
    ("MicroCapGems", "Micro Cap Gems", ["LOWCAP"], 7),
    
    # IDO & Launchpads
    ("ICODrops", "ICO Drops", ["IDO", "LOWCAP"], 10),
    ("CryptoRank", "CryptoRank", ["IDO", "LOWCAP"], 9),
    ("IDOAlert", "IDO Alert", ["IDO"], 9),
    ("LaunchpadHunter", "Launchpad Hunter", ["IDO"], 8),
    ("BinanceLaunchpad", "Binance Launchpad", ["IDO", "LISTING"], 10),
    ("BybitLaunchpad", "Bybit Launchpad", ["IDO", "LISTING"], 9),
    ("KuCoinLaunchpad", "KuCoin Launchpad", ["IDO", "LISTING"], 8),
    ("OKXJumpstart", "OKX Jumpstart", ["IDO", "LISTING"], 8),
    ("GateStartup", "Gate.io Startup", ["IDO", "LISTING"], 8),
    ("DAOMaker", "DAO Maker", ["IDO"], 9),
    ("TrustPad", "TrustPad", ["IDO"], 8),
    ("Seedify", "Seedify", ["IDO"], 8),
    ("PolkaStarter", "PolkaStarter", ["IDO"], 8),
    ("GameFiLaunchpad", "GameFi Launchpad", ["IDO"], 8),
    
    # Presale Trackers
    ("PresaleAlerts", "Presale Alerts", ["IDO", "LOWCAP"], 8),
    ("PrivateSale", "Private Sale", ["IDO", "LOWCAP"], 7),
    ("TokenSale", "Token Sale", ["IDO"], 7),
    
    # Research & Analytics
    ("DeFiResearch", "DeFi Research", ["LOWCAP", "DATA"], 8),
    ("GemResearch", "Gem Research", ["LOWCAP", "DATA"], 8),
    ("TokenInsight", "Token Insight", ["LOWCAP", "DATA"], 8),
    ("FundamentalsFirst", "Fundamentals First", ["LOWCAP"], 8),
]

# ==============================================================================
# TAG: AIRDROP & GUIDE - Airdrops & Tutorials
# ==============================================================================
AIRDROP_GUIDE_CHANNELS = [
    # Airdrop Hunters
    ("AirdropOfficial", "Airdrop Official", ["AIRDROP", "GUIDE"], 10),
    ("AirdropAlert", "Airdrop Alert", ["AIRDROP"], 9),
    ("AirdropHuntersClub", "Airdrop Hunters Club", ["AIRDROP"], 9),
    ("AirdropBob", "Airdrop Bob", ["AIRDROP", "GUIDE"], 9),
    ("AirdropNode", "Airdrop Node", ["AIRDROP"], 8),
    ("CryptoAirdrops", "Crypto Airdrops", ["AIRDROP"], 8),
    ("DailyAirdrop", "Daily Airdrop", ["AIRDROP"], 8),
    ("AirdropTracker", "Airdrop Tracker", ["AIRDROP"], 8),
    ("RetroHunter", "Retro Hunter", ["AIRDROP"], 9),
    ("TestnetGuide", "Testnet Guide", ["AIRDROP", "GUIDE"], 9),
    ("AirdropInspector", "Airdrop Inspector", ["AIRDROP"], 8),
    ("FreeDrops", "Free Drops", ["AIRDROP"], 7),
    ("AirdropKing", "Airdrop King", ["AIRDROP"], 7),
    ("CryptoFreeDrops", "Crypto Free Drops", ["AIRDROP"], 7),
    ("DropHunter", "Drop Hunter", ["AIRDROP"], 7),
    
    # Retroactive Farming
    ("RetroFarmer", "Retro Farmer", ["AIRDROP", "GUIDE"], 9),
    ("AirdropFarmer", "Airdrop Farmer", ["AIRDROP"], 8),
    ("LayerZeroFarm", "LayerZero Farm", ["AIRDROP"], 8),
    ("ZkSyncFarm", "zkSync Farm", ["AIRDROP"], 8),
    ("StarknetFarm", "Starknet Farm", ["AIRDROP"], 8),
    ("ScrollFarm", "Scroll Farm", ["AIRDROP"], 8),
    ("BaseAirdrop", "Base Airdrop", ["AIRDROP"], 8),
    
    # Vietnam Airdrop
    ("AirdropVietnam", "Airdrop Vietnam", ["AIRDROP"], 8),
    ("VNAirdrop", "VN Airdrop", ["AIRDROP"], 7),
    ("Coin98Airdrop", "Coin98 Airdrop", ["AIRDROP"], 8),
    
    # Guides & Tutorials
    ("CryptoGuide", "Crypto Guide", ["GUIDE"], 8),
    ("DeFiGuide", "DeFi Guide", ["GUIDE", "DEFI"], 8),
    ("TestnetTutorial", "Testnet Tutorial", ["GUIDE", "AIRDROP"], 8),
    ("CryptoTutorials", "Crypto Tutorials", ["GUIDE"], 7),
    ("BlockchainGuide", "Blockchain Guide", ["GUIDE"], 7),
    ("NFTGuide", "NFT Guide", ["GUIDE"], 7),
    ("Web3Tutorial", "Web3 Tutorial", ["GUIDE"], 7),
]

# ==============================================================================
# TAG: NARRATIVE & SENTIMENT - Sector Trends & Market Sentiment
# ==============================================================================
NARRATIVE_SENTIMENT_CHANNELS = [
    # Narrative Trackers
    ("NarrativeTracker", "Narrative Tracker", ["NARRATIVE"], 9),
    ("CryptoNarratives", "Crypto Narratives", ["NARRATIVE"], 9),
    ("SectorRotation", "Sector Rotation", ["NARRATIVE"], 8),
    ("TrendWatch", "Trend Watch", ["NARRATIVE"], 8),
    ("CryptoTrends", "Crypto Trends", ["NARRATIVE"], 8),
    ("MetaWatch", "Meta Watch", ["NARRATIVE"], 8),
    
    # AI & Tech Narratives
    ("AIcrypto", "AI Crypto", ["NARRATIVE"], 9),
    ("GPTCrypto", "GPT Crypto", ["NARRATIVE"], 8),
    ("AITokens", "AI Tokens", ["NARRATIVE"], 8),
    
    # RWA Narrative
    ("RWAWatch", "RWA Watch", ["NARRATIVE"], 9),
    ("RealWorldAssets", "Real World Assets", ["NARRATIVE"], 8),
    ("TokenizedRWA", "Tokenized RWA", ["NARRATIVE"], 8),
    
    # Meme & Gaming Narratives
    ("MemeCoinAlpha", "Meme Coin Alpha", ["NARRATIVE", "LOWCAP"], 8),
    ("GameFiAlerts", "GameFi Alerts", ["NARRATIVE"], 8),
    ("P2EGaming", "P2E Gaming", ["NARRATIVE"], 8),
    
    # Sentiment Analysis
    ("CryptoSentiment", "Crypto Sentiment", ["SENTIMENT"], 9),
    ("MarketSentiment", "Market Sentiment", ["SENTIMENT"], 9),
    ("FearGreedIndex", "Fear Greed Index", ["SENTIMENT"], 9),
    ("CryptoMood", "Crypto Mood", ["SENTIMENT"], 8),
    ("SocialTrends", "Social Trends", ["SENTIMENT"], 8),
    ("LunarCrush", "LunarCrush", ["SENTIMENT", "DATA"], 9),
    ("SantimentAlerts", "Santiment Alerts", ["SENTIMENT", "DATA"], 9),
    
    # Twitter/Social Trends
    ("CTTrending", "CT Trending", ["SENTIMENT"], 8),
    ("CryptoTwitter", "Crypto Twitter", ["SENTIMENT"], 8),
    ("ViralCrypto", "Viral Crypto", ["SENTIMENT"], 7),
    ("TrendingCoins", "Trending Coins", ["SENTIMENT"], 7),
    
    # Vietnam Sentiment
    ("CryptoVNSentiment", "Crypto VN Sentiment", ["SENTIMENT"], 7),
    ("VNMarketMood", "VN Market Mood", ["SENTIMENT"], 7),
]

# ==============================================================================
# TAG: SECURITY - Security Alerts & Hacks
# ==============================================================================
SECURITY_CHANNELS = [
    # Security Alert Channels
    ("CertiKAlert", "CertiK Alert", ["SECURITY"], 10),
    ("PeckShieldAlert", "PeckShield Alert", ["SECURITY"], 10),
    ("SlowMistAlert", "SlowMist Alert", ["SECURITY"], 10),
    ("CryptoSecAlert", "Crypto Sec Alert", ["SECURITY"], 9),
    ("HackTracker", "Hack Tracker", ["SECURITY"], 9),
    ("RugPullAlert", "Rug Pull Alert", ["SECURITY"], 9),
    ("ScamAlert", "Scam Alert", ["SECURITY"], 9),
    ("CryptoScamNews", "Crypto Scam News", ["SECURITY"], 8),
    ("BlockSecTeam", "BlockSec Team", ["SECURITY"], 9),
    ("DeFiSecurityNews", "DeFi Security News", ["SECURITY"], 8),
    ("SmartContractNews", "Smart Contract News", ["SECURITY"], 8),
    
    # Audit & Verification
    ("AuditAlerts", "Audit Alerts", ["SECURITY"], 8),
    ("TokenSniffer", "Token Sniffer", ["SECURITY"], 8),
    ("HoneypotDetector", "Honeypot Detector", ["SECURITY"], 8),
    ("RugCheck", "Rug Check", ["SECURITY"], 8),
    
    # Revoke & Protection
    ("RevokeAlert", "Revoke Alert", ["SECURITY"], 8),
    ("WalletGuard", "Wallet Guard", ["SECURITY"], 8),
    ("CryptoSafetyTips", "Crypto Safety Tips", ["SECURITY", "GUIDE"], 7),
]

# ==============================================================================
# TAG: DEFI - DeFi Protocols & Yield
# ==============================================================================
DEFI_CHANNELS = [
    # Top DeFi Protocols
    ("UniswapProtocol", "Uniswap", ["DEFI"], 10),
    ("AaveAave", "Aave", ["DEFI"], 10),
    ("Lido_fi", "Lido Finance", ["DEFI"], 10),
    ("MakerDAO", "MakerDAO", ["DEFI"], 10),
    ("CurveFinance", "Curve Finance", ["DEFI"], 9),
    ("Compound_finance", "Compound", ["DEFI"], 9),
    ("SushiSwap", "SushiSwap", ["DEFI"], 8),
    ("BalancerLabs", "Balancer", ["DEFI"], 8),
    ("1inchNetwork", "1inch", ["DEFI"], 9),
    ("daboratory", "dYdX", ["DEFI"], 9),
    ("GMX_io", "GMX", ["DEFI"], 9),
    ("PancakeSwap", "PancakeSwap", ["DEFI"], 9),
    ("TraderJoe", "Trader Joe", ["DEFI"], 8),
    ("Raydium", "Raydium", ["DEFI"], 8),
    ("Orca_so", "Orca", ["DEFI"], 8),
    ("JupiterExchange", "Jupiter", ["DEFI"], 9),
    
    # Yield & Farming
    ("YieldFarming", "Yield Farming", ["DEFI"], 8),
    ("DeFiYield", "DeFi Yield", ["DEFI"], 8),
    ("BestYieldFarms", "Best Yield Farms", ["DEFI"], 8),
    ("LiquidStaking", "Liquid Staking", ["DEFI"], 8),
    ("EigenLayer", "EigenLayer", ["DEFI"], 9),
    ("RestakingNews", "Restaking News", ["DEFI"], 8),
    
    # DeFi Analytics
    ("DeFiPulseNews", "DeFi Pulse News", ["DEFI", "DATA"], 8),
    ("DeFiNews", "DeFi News", ["DEFI", "NEWS_VIP"], 8),
    ("DeFiAlpha", "DeFi Alpha", ["DEFI"], 8),
    ("DeFiDaily", "DeFi Daily", ["DEFI"], 7),
    
    # Layer 2 DeFi
    ("ArbitrumDeFi", "Arbitrum DeFi", ["DEFI"], 8),
    ("OptimismDeFi", "Optimism DeFi", ["DEFI"], 8),
    ("ZkSyncDeFi", "zkSync DeFi", ["DEFI"], 8),
    ("BaseDeFi", "Base DeFi", ["DEFI"], 8),
]

# ==============================================================================
# TAG: DATA - Market Data & Analytics
# ==============================================================================
DATA_CHANNELS = [
    # Data Aggregators
    ("CoinGeckoData", "CoinGecko Data", ["DATA"], 10),
    ("CMCData", "CMC Data", ["DATA"], 10),
    ("TradingViewData", "TradingView Data", ["DATA", "SIGNAL"], 9),
    ("CryptoCompareData", "CryptoCompare Data", ["DATA"], 8),
    ("CoinPaprika", "CoinPaprika", ["DATA"], 8),
    
    # On-chain Data
    ("GlassnodeData", "Glassnode Data", ["DATA", "ONCHAIN"], 10),
    ("CryptoQuantData", "CryptoQuant Data", ["DATA", "ONCHAIN"], 10),
    ("NansenData", "Nansen Data", ["DATA", "ONCHAIN"], 9),
    ("DuneData", "Dune Data", ["DATA", "ONCHAIN"], 9),
    ("TokenTerminalData", "Token Terminal Data", ["DATA"], 8),
    
    # Market Data
    ("OpenInterest", "Open Interest", ["DATA"], 9),
    ("FundingRates", "Funding Rates", ["DATA"], 9),
    ("LiquidationData", "Liquidation Data", ["DATA"], 9),
    ("FuturesData", "Futures Data", ["DATA"], 8),
    ("OptionsData", "Options Data", ["DATA"], 8),
    ("VolumeTracker", "Volume Tracker", ["DATA"], 8),
    ("MarketCapTracker", "Market Cap Tracker", ["DATA"], 7),
    
    # Derivatives Data
    ("CoinGlass", "CoinGlass", ["DATA"], 9),
    ("Laevitas", "Laevitas", ["DATA"], 8),
    ("TheBlock_Data", "The Block Data", ["DATA", "NEWS_VIP"], 9),
    ("SkewData", "Skew Data", ["DATA"], 8),
]


async def resolve_and_insert(client: TelegramClient, channels_list: list, category_name: str):
    """Resolve usernames to chat_ids and insert into database"""
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    async with AsyncSessionLocal() as session:
        for username, name, tags, priority in channels_list:
            try:
                # Check if already exists by name
                stmt = select(SourceConfig).where(SourceConfig.name == name)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    logger.info(f"⏭️  Skip {name} - already exists")
                    skip_count += 1
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
                        logger.info(f"⏭️  Skip {name} - chat_id exists")
                        skip_count += 1
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
                    
                    success_count += 1
                    logger.info(f"✅ [{success_count}] Added: {name} ({chat_id})")
                    
                    # Random delay 40-60s to avoid FloodWait
                    delay = random.randint(40, 60)
                    logger.info(f"⏳ Waiting {delay}s...")
                    await asyncio.sleep(delay)
                    
                except UsernameNotOccupiedError:
                    logger.warning(f"❌ Not found: @{username}")
                    error_count += 1
                except ChannelPrivateError:
                    logger.warning(f"🔒 Private: @{username}")
                    error_count += 1
                except FloodWaitError as e:
                    logger.warning(f"⏳ FloodWait: {e.seconds}s")
                    await asyncio.sleep(e.seconds + 10)
                except Exception as e:
                    logger.error(f"❌ Error @{username}: {e}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Error {name}: {e}")
                await session.rollback()
                error_count += 1
    
    logger.info(f"📊 {category_name}: ✅{success_count} ⏭️{skip_count} ❌{error_count}")
    return success_count, skip_count, error_count


async def main():
    """Main function"""
    logger.info("🚀 Starting FULL source seeding...")
    logger.info("=" * 60)
    
    # Detect environment
    is_windows = os.name == 'nt'
    
    if is_windows:
        # Windows: use 84389961241 with proxy
        session_name = "84389961241"
    else:
        # Linux VPS: use ingestor_session (it's working, 84389961241 is corrupted)
        session_name = "ingestor_session"
    
    session_path = os.path.join(os.getcwd(), "sessions", session_name)
    
    if not os.path.exists(f"{session_path}.session"):
        logger.error(f"❌ Session not found: {session_path}.session")
        return
    
    # Load proxy config (only for Windows)
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
                    logger.info(f"🔐 Proxy: {p['hostname']}:{p['port']}")
    
    logger.info(f"📱 Session: {session_name}")
    
    # Create client
    client = TelegramClient(
        session_path,
        settings.API_ID,
        settings.API_HASH,
        proxy=proxy
    )
    
    try:
        await client.start()
        logger.info("📱 Connected to Telegram\n")
        
        total_success = 0
        total_skip = 0
        total_error = 0
        
        # Process all categories
        categories = [
            ("🐋 ONCHAIN & WHALE", ONCHAIN_WHALE_CHANNELS),
            ("📊 SIGNAL & KOLS", SIGNAL_KOLS_CHANNELS),
            ("📰 NEWS & LISTING", NEWS_LISTING_CHANNELS),
            ("💎 LOWCAP & IDO", LOWCAP_IDO_CHANNELS),
            ("🎁 AIRDROP & GUIDE", AIRDROP_GUIDE_CHANNELS),
            ("🔥 NARRATIVE & SENTIMENT", NARRATIVE_SENTIMENT_CHANNELS),
            ("🔒 SECURITY", SECURITY_CHANNELS),
            ("🏦 DEFI", DEFI_CHANNELS),
            ("📈 DATA", DATA_CHANNELS),
        ]
        
        for cat_name, channels in categories:
            logger.info(f"\n{'='*60}")
            logger.info(f"{cat_name} ({len(channels)} channels)")
            logger.info("=" * 60)
            
            s, sk, e = await resolve_and_insert(client, channels, cat_name)
            total_success += s
            total_skip += sk
            total_error += e
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🏁 COMPLETED!")
        logger.info(f"   ✅ Added: {total_success}")
        logger.info(f"   ⏭️  Skipped: {total_skip}")
        logger.info(f"   ❌ Errors: {total_error}")
        logger.info("=" * 60)
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
