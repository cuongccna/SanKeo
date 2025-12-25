TEMPLATE_CONFIG = {
    "WHALE_HUNTING": {
        "name": "Cá Mập Săn Mồi",
        "theme_color": "#FFD700", # Vàng Gold
        "alert_level": "HIGH",
        "visual_style": "DEFAULT",
        "ai_prompt": """
            Bạn là chuyên gia On-chain. Trích xuất dữ liệu từ các tin nhắn dưới đây:
            - Tổng volume cá voi di chuyển.
            - Nguồn (From) và Đích (To).
            - Nhận định rủi ro (Low/Medium/High).
            
            JSON Output keys: {"action_summary", "metrics": {"Volume": "...", "From": "...", "To": "...", "Risk": "..."}}
        """
    },
    "LOWCAP_GEM": {
        "name": "Kèo Lowcap/Hidden Gem",
        "theme_color": "#00FF00", # Xanh lá Matrix
        "visual_style": "DEFAULT",
        "ai_prompt": """
            Bạn là thợ săn Gem. Trích xuất dữ liệu:
            - Tên Token ($TAG).
            - Số nhóm đang shill.
            - Điểm rủi ro (1-10) dựa trên check ví/contract.
            
            JSON Output keys: {"action_summary", "metrics": {"Token": "...", "Shill Count": "...", "Risk Score": "...", "Entry": "..."}}
        """
    },
    "SENTIMENT_SNIPER": {
        "name": "Tâm Lý Đám Đông",
        "theme_color": "#00BFFF", # Xanh dương
        "visual_style": "GAUGE", 
        "ai_prompt": """
            Phân tích tâm lý đám đông.
            JSON Output keys: {"action_summary", "metrics": {"Sentiment Score": "0-100", "Emotion": "Fear/Greed", "Top Topic": "..."}}
        """
    },
    "SECURITY_ALERT": {
        "name": "Báo Động Bảo Mật",
        "theme_color": "#FF4500", # Đỏ cam
        "visual_style": "ALERT",
        "ai_prompt": """
            Cảnh báo Hack/Exploit.
            JSON Output keys: {"action_summary", "metrics": {"Type": "Hack/Scam", "Loss": "$...", "Action": "Revoke/Withdraw"}}
        """
    },
    "AIRDROP_HUNTER": {
        "name": "Săn Airdrop",
        "theme_color": "#DDA0DD", # Tím mộng mơ
        "visual_style": "STEP_LIST", 
        "ai_prompt": """
            Hướng dẫn làm Airdrop.
            JSON Output keys: {"action_summary", "metrics": {"Project": "...", "Cost": "...", "Time": "..."}, "steps": ["Step 1...", "Step 2..."]}
        """
    },
    "TREND_CONFLICT": {
        "name": "Phân Tích Đa Chiều",
        "theme_color": "#FF69B4", # Hot Pink
        "visual_style": "DEFAULT",
        "ai_prompt": """
            Phân tích các luồng thông tin trái chiều.
            JSON Output keys: {"action_summary", "metrics": {"Bullish Signals": "...", "Bearish Signals": "...", "Conclusion": "..."}}
        """
    }
}

def get_template_config(code: str):
    return TEMPLATE_CONFIG.get(code, {
        "name": "General Report",
        "theme_color": "#FFFFFF",
        "ai_prompt": "Tóm tắt tin nhắn. JSON Output keys: {'action_summary', 'metrics': {}}",
        "visual_style": "DEFAULT"
    })
