import asyncio
import json
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import AnalysisTemplate
from src.common.logger import get_logger

logger = get_logger("seed_templates")

TEMPLATES = [
    {
        "code": "WHALE_HUNTING",
        "name": "🐋 Cá Mập Săn Mồi (Whale Hunting)",
        "required_tags": ["ONCHAIN", "SIGNAL"],
        "time_window_minutes": 60,
        "prompt_template": """
        Bạn là chuyên gia săn cá mập (Whale Hunter).
        Dựa trên dữ liệu On-chain (chuyển tiền lên/xuống sàn) và hành động giá (Price Action) dưới đây:
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - Phân tích hành vi cá voi: Đang gom hàng (Accumulation) hay chuẩn bị xả (Distribution)?
        - Kết hợp với hành động giá hiện tại để đưa ra cảnh báo (Ví dụ: Chuyển tiền lên sàn + Giá tại kháng cự -> Rủi ro xả).
        - Đưa ra nhận định ngắn hạn: Bullish hay Bearish?
        """
    },
    {
        "code": "HIDDEN_GEM",
        "name": "💎 Kèo Lowcap/Hidden Gem",
        "required_tags": ["LOWCAP", "SIGNAL"],
        "time_window_minutes": 120,
        "prompt_template": """
        Bạn là chuyên gia săn kèo Lowcap/Xổ số.
        Dựa trên các tín hiệu shill từ cộng đồng và dữ liệu volume dưới đây:
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - Xác định token nào đang được nhắc đến nhiều nhất (Shill frequency).
        - Đánh giá rủi ro (Rug pull, Honey pot) dựa trên thông tin có được.
        - Khuyến nghị vốn vào lệnh (Ví dụ: Chỉ xổ số, Volume đột biến).
        - Chấm điểm rủi ro trên thang 10.
        """
    },
    {
        "code": "SENTIMENT_SNIPER",
        "name": "😡 Tâm Lý Đám Đông (Sentiment Sniper)",
        "required_tags": ["NEWS_VIP", "SENTIMENT"],
        "time_window_minutes": 60,
        "prompt_template": """
        Bạn là chuyên gia phân tích tâm lý thị trường (Sentiment Analysis).
        Dựa trên tin tức và phản ứng của cộng đồng dưới đây:
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - Xác định tâm lý chủ đạo: Sợ hãi (Fear), Hưng phấn (Greed) hay Thờ ơ?
        - Tìm kiếm sự phân kỳ (Ví dụ: Tin xấu ra nhiều nhưng giá không giảm -> Đáy).
        - Dự đoán phản ứng giá tiếp theo dựa trên tâm lý đám đông.
        """
    },
    {
        "code": "TREND_CONFLICT",
        "name": "⚔️ Phân Tích Đa Chiều (Trend Conflict)",
        "required_tags": ["SIGNAL", "NEWS_VIP"],
        "time_window_minutes": 60,
        "prompt_template": """
        Bạn là chuyên gia chiến lược thị trường.
        Nhiệm vụ của bạn là tìm sự xung đột hoặc đồng thuận giữa Phân tích kỹ thuật (PTKT) và Tin tức Vĩ mô (Macro).
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - So sánh tín hiệu kỹ thuật (Long/Short) với tin tức vĩ mô (Tốt/Xấu).
        - Nếu xung đột (Ví dụ: PTKT báo Mua nhưng Vĩ mô Xấu), hãy đưa ra cảnh báo và chiến lược an toàn (Scalp/Đứng ngoài).
        - Nếu đồng thuận, xác nhận xu hướng mạnh.
        """
    },
    {
        "code": "AIRDROP_HUNTER",
        "name": "🪂 Săn Airdrop/Retroactive",
        "required_tags": ["AIRDROP", "GUIDE"],
        "time_window_minutes": 240, # 4 hours window for guides
        "prompt_template": """
        Bạn là chuyên gia hướng dẫn làm Airdrop/Retroactive.
        Tổng hợp các hướng dẫn và tin tức mới nhất về Airdrop từ dữ liệu dưới đây:
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - Xác định dự án/hệ sinh thái nào đang hot (Ví dụ: zkSync, LayerZero).
        - Tóm tắt các bước thực hiện nhiệm vụ một cách ngắn gọn, dễ hiểu nhất (Step-by-step).
        - Lưu ý các hạn chót (Deadline) hoặc yêu cầu vốn nếu có.
        """
    },
    {
        "code": "SECURITY_ALERT",
        "name": "🛡️ Bảo Mật & Rủi Ro (Security Alert)",
        "required_tags": ["SECURITY", "NEWS_VIP"],
        "time_window_minutes": 30, # Fast reaction
        "prompt_template": """
        Bạn là chuyên gia bảo mật Blockchain.
        Phân tích các tin tức về Hack, Exploit, hoặc FUD sàn giao dịch dưới đây:
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - Xác định mức độ nghiêm trọng: Thấp, Trung bình, hay Khẩn cấp (Critical).
        - Token/Giao thức nào bị ảnh hưởng trực tiếp?
        - Đưa ra hành động khuyến nghị ngay lập tức cho người dùng (Ví dụ: Rút tiền, Revoke quyền, Bán tháo).
        """
    },
    {
        "code": "EXCHANGE_FLOW",
        "name": "🌊 Dòng Chảy Sàn (Exchange Flow)",
        "required_tags": ["ONCHAIN", "DATA"],
        "time_window_minutes": 120,
        "prompt_template": """
        Bạn là chuyên gia phân tích dữ liệu On-chain (Glassnode/CryptoQuant).
        Tập trung vào dòng tiền nạp/rút (Inflow/Outflow) trên các sàn giao dịch.
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - Tổng hợp xu hướng dòng tiền: Net Inflow (Nạp ròng -> Áp lực bán) hay Net Outflow (Rút ròng -> Tích lũy).
        - Đánh giá tác động lên giá BTC/ETH trong trung hạn.
        - Kết luận: Tín hiệu Tích cực hay Tiêu cực?
        """
    },
    {
        "code": "NARRATIVE_TREND",
        "name": "🌊 Narrative Trend (Bắt sóng)",
        "required_tags": ["NARRATIVE", "NEWS_VIP"],
        "time_window_minutes": 120,
        "prompt_template": """
        Bạn là chuyên gia nắm bắt xu hướng (Trend Spotter).
        Dựa trên tin tức công nghệ và biến động giá các coin dẫn đầu:
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - Xác định Narrative nào đang hút dòng tiền (Ví dụ: AI, RWA, GameFi, Meme).
        - Liệt kê các token nổi bật trong trend đang tăng trưởng.
        - Đánh giá độ bền của trend: Mới chớm nở hay đã FOMO quá đà?
        """
    },
    {
        "code": "MORNING_BRIEF",
        "name": "☕ Tổng Hợp Đầu Ngày (Morning Brief)",
        "required_tags": ["NEWS_VIP", "SIGNAL", "ONCHAIN"],
        "time_window_minutes": 720, # 12 hours window
        "prompt_template": """
        Bạn là trợ lý tổng hợp tin tức tài chính cá nhân.
        Hãy tạo một bản báo cáo tóm tắt thị trường trong 12-24h qua dành cho người bận rộn.
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - Chọn ra 3-5 tin tức quan trọng nhất ảnh hưởng đến thị trường.
        - Tóm tắt diễn biến giá BTC và các Altcoin chính.
        - Giọng văn: Chuyên nghiệp, ngắn gọn, chào buổi sáng.
        """
    },
    {
        "code": "KOL_LEADERBOARD",
        "name": "🏆 Soi Kèo KOLs (Leaderboard)",
        "required_tags": ["KOLS", "SIGNAL"],
        "time_window_minutes": 120,
        "prompt_template": """
        Bạn là trọng tài theo dõi hiệu suất các KOLs/Admin nhóm tín hiệu.
        Tổng hợp các kèo (Call) từ các nguồn dưới đây:
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - Thống kê sự đồng thuận: Bao nhiêu nguồn đang hô Long? Bao nhiêu hô Short?
        - Nếu có sự đồng thuận cao (>70%), hãy đánh dấu là "Tín hiệu mạnh".
        - Liệt kê các mức Entry/TP phổ biến nhất mà các KOLs đang nhắm tới.
        """
    },
    {
        "code": "SMART_MONEY_TRACKER",
        "name": "🧠 Smart Money Tracker",
        "required_tags": ["ONCHAIN", "NEWS_VIP"],
        "time_window_minutes": 120,
        "prompt_template": """
        Bạn là chuyên gia theo dấu dòng tiền thông minh (Smart Money/Insiders).
        Kết hợp dữ liệu On-chain (ví cá mập, ví sàn) và Tin tức nội bộ để tìm ra các cơ hội ẩn.
        
        Dữ liệu:
        {list_of_messages}
        
        Yêu cầu:
        - Phát hiện các token đang được Smart Money gom âm thầm (Accumulation) trước khi có tin tức.
        - Phân tích logic đằng sau các hành động này (Ví dụ: Gom trước thềm nâng cấp, Listing).
        - Đề xuất chiến lược: Theo dõi (Watchlist) hay Vào lệnh ngay (Action)?
        - Cảnh báo nếu đây là bẫy thanh khoản (Liquidity Trap).
        """
    }
]

async def seed_templates():
    async with AsyncSessionLocal() as session:
        for tpl_data in TEMPLATES:
            # Check if exists
            result = await session.execute(select(AnalysisTemplate).where(AnalysisTemplate.code == tpl_data["code"]))
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"Template {tpl_data['code']} already exists. Updating...")
                existing.name = tpl_data["name"]
                existing.required_tags = tpl_data["required_tags"]
                existing.time_window_minutes = tpl_data["time_window_minutes"]
                existing.prompt_template = tpl_data["prompt_template"]
            else:
                logger.info(f"Creating template {tpl_data['code']}...")
                new_tpl = AnalysisTemplate(
                    code=tpl_data["code"],
                    name=tpl_data["name"],
                    required_tags=tpl_data["required_tags"],
                    time_window_minutes=tpl_data["time_window_minutes"],
                    prompt_template=tpl_data["prompt_template"]
                )
                session.add(new_tpl)
        
        await session.commit()
        logger.info("Templates seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_templates())
