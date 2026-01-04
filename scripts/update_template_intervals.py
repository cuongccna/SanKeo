"""
Script cập nhật khoảng thời gian gửi báo cáo định kỳ cho các templates.
Giãn thời gian để không gửi liên tục.
"""
import asyncio
import sys
import os

sys.path.append(os.getcwd())

from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import AnalysisTemplate
from src.common.logger import get_logger

logger = get_logger("update_intervals")

# Cấu hình khoảng thời gian (phút) cho từng template
# Có thể điều chỉnh theo nhu cầu
TEMPLATE_INTERVALS = {
    # On-chain & Whales - Cần real-time hơn
    "WHALE_HUNTING": 120,      # 2 giờ
    "SMART_MONEY": 180,        # 3 giờ
    
    # Market Opportunities - Cập nhật thường xuyên vừa phải
    "LOWCAP_GEM": 240,         # 4 giờ
    "EXCHANGE_LISTING": 360,   # 6 giờ
    
    # Technical Analysis - Theo phiên giao dịch
    "MARKET_SENTIMENT": 240,   # 4 giờ
    "BTC_ANALYSIS": 180,       # 3 giờ
    "ALTCOIN_SEASON": 360,     # 6 giờ
    
    # News & Macro - Ít urgent hơn
    "CRYPTO_NEWS": 480,        # 8 giờ
    "MACRO_ANALYSIS": 720,     # 12 giờ
    
    # Default cho các template khác
    "_DEFAULT": 240,           # 4 giờ
}

async def update_intervals():
    async with AsyncSessionLocal() as session:
        logger.info("Bắt đầu cập nhật khoảng thời gian gửi báo cáo...")
        
        # Lấy tất cả templates
        stmt = select(AnalysisTemplate)
        result = await session.execute(stmt)
        templates = result.scalars().all()
        
        updated_count = 0
        for template in templates:
            old_interval = template.time_window_minutes
            new_interval = TEMPLATE_INTERVALS.get(
                template.code, 
                TEMPLATE_INTERVALS["_DEFAULT"]
            )
            
            if old_interval != new_interval:
                template.time_window_minutes = new_interval
                logger.info(
                    f"[{template.code}] {template.name}: "
                    f"{old_interval} phút → {new_interval} phút"
                )
                updated_count += 1
            else:
                logger.info(f"[{template.code}] Không thay đổi ({old_interval} phút)")
        
        await session.commit()
        
        logger.info("=" * 50)
        logger.info(f"✅ Đã cập nhật {updated_count} templates")
        logger.info("=" * 50)
        
        # Hiển thị bảng tổng hợp
        print("\n📊 BẢNG THỜI GIAN GỬI BÁO CÁO ĐỊNH KỲ:")
        print("-" * 50)
        print(f"{'Template':<25} {'Interval':<15} {'Mô tả'}")
        print("-" * 50)
        
        for template in templates:
            hours = template.time_window_minutes / 60
            if hours >= 1:
                desc = f"{hours:.1f} giờ/lần"
            else:
                desc = f"{template.time_window_minutes} phút/lần"
            print(f"{template.code:<25} {template.time_window_minutes:<15} {desc}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(update_intervals())
