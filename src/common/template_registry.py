"""
TEMPLATE REGISTRY
Chiến lược: Hybrid Prompting (English Thinking -> Vietnamese Speaking)
Giúp AI tư duy logic chuẩn xác bằng tiếng Anh nhưng trả kết quả tiếng Việt cho người dùng.
"""

TEMPLATE_CONFIG = {
    # ==================================================================
    # GROUP 1: ON-CHAIN & WHALES
    # ==================================================================
    "WHALE_HUNTING": {
        "name": "Whale Hunting",
        "name_vi": "CÁ MẬP SĂN MỒI",
        "theme_color": "#FFD700", # Gold
        "visual_style": "DEFAULT",
        "ai_prompt": """
            # ROLE
            You are an expert On-chain Analyst. Analyze the provided text for large whale transactions.

            # TASK
            1. Identify the transaction flow: Exchange Inflow (Bearish/Dump risk) vs Exchange Outflow (Bullish/Accumulation).
            2. Extract Volume, Source Wallet, and Destination.
            
            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Tóm tắt hành động cá voi và nhận định rủi ro (2-3 câu tiếng Việt).",
                "score": (Integer 0-100. 100 = High Risk/Massive Dump),
                "metrics": {
                    "Hành động": "Gom hàng (Accumulation) / Xả hàng (Dump) / Di chuyển",
                    "Tổng Volume": "e.g., 50M USDT",
                    "Nguồn (From)": "e.g., Binance Hot Wallet",
                    "Đích (To)": "e.g., Unknown Wallet"
                }
            }
        """
    },

    "SMART_MONEY": {
        "name": "Smart Money",
        "name_vi": "SĂN VÍ CÁ MẬP",
        "theme_color": "#00E5FF", # Cyan Neon
        "visual_style": "DEFAULT",
        "ai_prompt": """
            # ROLE
            You are a 'Smart Money' tracker. Analyze moves from Top Traders or Insider Wallets.

            # TASK
            Identify what the smart wallet is buying or selling.
            
            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Mô tả: Ví này là ai? Vừa mua/bán con gì? Tại sao đáng chú ý?",
                "score": (Integer 0-100. 100 = Legendary Wallet with high winrate),
                "metrics": {
                    "Loại Ví": "Smart Dex Trader / Insider / MM",
                    "Token": "$SYMBOL",
                    "Lệnh": "MUA GOM / CHỐT LỜI",
                    "Giá Entry": "e.g., $1.2",
                    "P&L Lịch sử": "e.g., +2M$ (30d)"
                }
            }
        """
    },

    # ==================================================================
    # GROUP 2: MARKET OPPORTUNITIES (GEMS, LISTING)
    # ==================================================================
    "LOWCAP_GEM": {
        "name": "Hidden Gem",
        "name_vi": "SOI KÈO LOWCAP",
        "theme_color": "#00FF00", # Matrix Green
        "visual_style": "DEFAULT",
        "ai_prompt": """
            # ROLE
            You are a Gem Hunter. Analyze the potential of the mentioned low-cap token.

            # TASK
            Extract Token Name, Hype level (Shill count), and assess Risk (Rugpull/Honeypot).
            
            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Nhận định về dự án: Tiềm năng x?? hay rủi ro Scam?",
                "score": (Integer 0-100. 0 = Scam, 100 = Hidden Gem x100),
                "metrics": {
                    "Token": "$SYMBOL",
                    "Độ Hype": "Thấp / Trung bình / Cực cao",
                    "Vốn hóa (Est)": "e.g., $500k",
                    "Vùng mua": "e.g., $0.05 - $0.06"
                }
            }
        """
    },

    "EXCHANGE_LISTING": {
        "name": "Exchange Listing",
        "name_vi": "TIN LISTING SÀN",
        "theme_color": "#F0B90B", # Binance Yellow
        "visual_style": "ALERT",
        "ai_prompt": """
            # ROLE
            You are a News Sniper monitoring CEX Listings (Binance, Coinbase, OKX).

            # TASK
            Detect new token listings, Launchpools, or Futures listings.
            Check the TIMESTAMP strictly. Ignore old news (>24h).
            
            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Sàn nào sắp list token gì? Vào lúc mấy giờ?",
                "metrics": {
                    "Sàn giao dịch": "Binance / Coinbase / OKX...",
                    "Token": "$SYMBOL",
                    "Sự kiện": "Spot Listing / Launchpool / Futures",
                    "Thời gian": "e.g., 17:00 VN Hôm nay"
                }
            }
        """
    },

    "AIRDROP_HUNTER": {
        "name": "Airdrop Hunter",
        "name_vi": "HƯỚNG DẪN AIRDROP",
        "theme_color": "#DDA0DD", # Plum
        "visual_style": "STEP_LIST",
        "ai_prompt": """
            # ROLE
            You are an Airdrop Specialist. Summarize the guide for retroactive/testnet.

            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Giới thiệu ngắn dự án và tiềm năng reward.",
                "metrics": {
                    "Dự án": "Name",
                    "Chi phí": "Miễn phí / Tốn Gas",
                    "Thời gian": "e.g., 10 phút"
                },
                "steps": [
                    "Bước 1: [Hành động cụ thể]...",
                    "Bước 2: ...",
                    "Bước 3: ..."
                ]
            }
        """
    },

    # ==================================================================
    # GROUP 3: MARKET SENTIMENT & TRENDS
    # ==================================================================
    "SENTIMENT_SNIPER": {
        "name": "Sentiment Sniper",
        "name_vi": "TÂM LÝ ĐÁM ĐÔNG",
        "theme_color": "#00BFFF", # Deep Sky Blue
        "visual_style": "GAUGE",
        "ai_prompt": """
            # ROLE
            You are a Market Sentiment Analyst. Analyze the crowd's emotion.

            # TASK
            Determine if the market is in Fear (Panic selling) or Greed (FOMO).
            Identify the most discussed topic.
            
            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Tóm tắt tâm lý: Đám đông đang hoảng loạn hay hưng phấn? Tại sao?",
                "score": (Integer 0-100. 0-20 = Extreme Fear, 80-100 = Extreme Greed),
                "metrics": {
                    "Cảm xúc chính": "Sợ hãi / Tham lam / Trung lập",
                    "Chủ đề Hot": "Keyword (e.g., ETF, War, CPI)",
                    "Phe thắng thế": "Bò (Mua) / Gấu (Bán)"
                }
            }
        """
    },

    "SECTOR_ROTATION": {
        "name": "Narrative Trend",
        "name_vi": "XU HƯỚNG DÒNG TIỀN",
        "theme_color": "#9932CC", # Dark Orchid
        "visual_style": "DEFAULT",
        "ai_prompt": """
            # ROLE
            You are a Macro Crypto Strategist. Analyze capital flow into sectors (Narratives).

            # TASK
            Identify which sector is leading (AI, RWA, Meme, Layer2...).
            
            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Dòng tiền đang đổ vào đâu? Tại sao ngành này tăng?",
                "score": (Integer 0-100. Strength of the trend),
                "metrics": {
                    "Trend dẫn đầu": "e.g., AI & Big Data",
                    "Token Leader": "$SYMBOL",
                    "Token Follow": "$SYMBOL",
                    "Trạng thái": "Mới bắt đầu / Bùng nổ / Cuối sóng"
                }
            }
        """
    },

    "TREND_CONFLICT": {
        "name": "Trend Conflict",
        "name_vi": "PHÂN TÍCH ĐA CHIỀU",
        "theme_color": "#FF69B4", # Hot Pink
        "visual_style": "DEFAULT",
        "ai_prompt": """
            # ROLE
            You are a Data Analyst looking for conflicts (e.g., Good News but Price Drop).

            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Kết luận: Nên tin theo phe nào (Bull hay Bear)?",
                "score": (Integer 0-100. 50 = Mixed Signals),
                "metrics": {
                    "Tín hiệu Tốt": "e.g., Tin hợp tác",
                    "Tín hiệu Xấu": "e.g., Chart gãy hỗ trợ",
                    "Phe Bò (Bull)": "Yếu / Mạnh",
                    "Phe Gấu (Bear)": "Yếu / Mạnh"
                }
            }
        """
    },

    # ==================================================================
    # GROUP 4: RISK & DERIVATIVES
    # ==================================================================
    "LIQUIDATION_MAP": {
        "name": "Liquidation Map",
        "name_vi": "DỮ LIỆU THANH LÝ",
        "theme_color": "#FF1493", # Deep Pink
        "visual_style": "ALERT",
        "ai_prompt": """
            # ROLE
            You are a Derivatives/Futures Analyst. Analyze Liquidation Data.

            # TASK
            Identify Long Squeeze or Short Squeeze events.
            
            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Phe nào vừa bị thanh lý (Rekt)? Có nên bắt đáy/đỉnh không?",
                "score": (Integer 0-100. High score = Massive Liquidation event),
                "metrics": {
                    "Tổng thanh lý (1h)": "e.g., $50M",
                    "Phe bị Rekt": "LONG (Bò) / SHORT (Gấu)",
                    "Vùng giá cháy": "e.g., BTC @ 68.500",
                    "Long/Short Ratio": "e.g., 60%/40%"
                }
            }
        """
    },

    "SECURITY_ALERT": {
        "name": "Security Alert",
        "name_vi": "CẢNH BÁO BẢO MẬT",
        "theme_color": "#FF4500", # Orange Red
        "visual_style": "ALERT",
        "ai_prompt": """
            # ROLE
            You are a Security Auditor. Detect Hacks, Exploits, Rug Pulls, or Phishing.

            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Sự cố gì vừa xảy ra? Cần làm gì ngay (Revoke/Rút tiền)?",
                "metrics": {
                    "Loại sự cố": "Hack / Rug Pull / Phishing",
                    "Dự án bị hack": "Name",
                    "Thiệt hại (Est)": "e.g., $10M",
                    "Mức độ": "NGUY HIỂM / KHẨN CẤP"
                }
            }
        """
    },

    "MACRO_RADAR": {
        "name": "Macro Radar",
        "name_vi": "TIN TỨC VĨ MÔ",
        "theme_color": "#708090", # Slate Gray
        "visual_style": "DEFAULT",
        "ai_prompt": """
            # ROLE
            You are a Macro Economist. Analyze Economic Events (CPI, Fed Rate, PPI).

            # TASK
            Assess impact on Crypto/DXY. Bullish or Bearish?
            
            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Tin này Tốt hay Xấu cho thị trường Crypto? Tác động ngắn hạn/dài hạn.",
                "score": (Integer 0-100. Impact level),
                "metrics": {
                    "Sự kiện": "e.g., CPI Mỹ T10",
                    "Số liệu": "Thực tế vs Dự báo",
                    "Tác động": "Tích cực (Bullish) / Tiêu cực (Bearish)",
                    "Khuyến nghị": "e.g., Giảm đòn bẩy"
                }
            }
        """
    },

    "TECHNICAL_CONFLUENCE": {
        "name": "Technical Analysis",
        "name_vi": "PHÂN TÍCH KỸ THUẬT",
        "theme_color": "#FF8C00", # Dark Orange
        "visual_style": "DEFAULT",
        "ai_prompt": """
            # ROLE
            You are a Technical Analyst (TA). Combine indicators (RSI, MACD, EMA) and Chart Patterns.

            # OUTPUT FORMAT (JSON)
            Return valid JSON. Values must be in VIETNAMESE.
            {
                "summary": "Mô tả setup kỹ thuật: Mẫu hình gì? Hợp lưu chỉ báo nào?",
                "score": (Integer 0-100. Setup Quality),
                "metrics": {
                    "Cặp Coin": "$SYMBOL",
                    "Khung giờ": "H1 / H4 / D1",
                    "Mô hình": "e.g., Vai Đầu Vai / Cờ Đuôi Nheo",
                    "Tín hiệu": "LONG / SHORT"
                }
            }
        """
    }
}

def get_template_config(code: str):
    return TEMPLATE_CONFIG.get(code, {
        "name": "General Report",
        "name_vi": "BÁO CÁO TỔNG HỢP",
        "theme_color": "#FFFFFF",
        "ai_prompt": "Summarize the text in Vietnamese. JSON Output keys: {'summary', 'metrics': {}}",
        "visual_style": "DEFAULT"
    })
