import re
import json
from src.common.logger import get_logger
from src.worker.ai_engine import ai_engine

logger = get_logger("strategy_processor")

class StrategyProcessor:
    """
    Xử lý tin nhắn theo chiến lược dựa trên Tag.
    """
    
    async def process(self, message_data: dict) -> dict:
        """
        Điều phối xử lý dựa trên tag.
        Trả về message_data đã được làm giàu (enriched) hoặc format lại.
        """
        tag = message_data.get("tag", "NORMAL")
        text = message_data.get("text", "")
        
        if not text:
            return message_data

        try:
            if tag == "NEWS_VIP":
                message_data["text"] = await self.handle_news_vip(text)
            elif tag == "SIGNAL":
                message_data["text"] = await self.handle_signal(text)
            elif tag == "ONCHAIN":
                message_data["text"] = await self.handle_onchain(text)
            # NORMAL tag does nothing
            
        except Exception as e:
            logger.error(f"Strategy processing failed for tag {tag}: {e}")
            # Fallback: return original message
            
        return message_data

    async def handle_news_vip(self, text: str) -> str:
        """
        Xử lý tin tức VIP: Tóm tắt + Cảnh báo Listing/Hack.
        """
        # 1. Check keywords for icons
        prefix = ""
        if any(kw in text.lower() for kw in ["listing", "list", "niêm yết"]):
            prefix += "🚨 **LISTING ALERT** 🚨\n"
        if any(kw in text.lower() for kw in ["hack", "exploit", "attack"]):
            prefix += "⚠️ **SECURITY ALERT** ⚠️\n"

        # 2. AI Summary
        prompt = f"""
        Bạn là biên tập viên tin tức Crypto chuyên nghiệp.
        Hãy tóm tắt tin tức sau thành ĐÚNG 1 DÒNG tiếng Việt ngắn gọn, súc tích.
        Giữ lại các con số quan trọng (giá, volume, %).
        
        Tin tức:
        {text}
        """
        
        summary = await ai_engine.generate_text(prompt)
        if not summary:
            summary = text[:200] + "..." # Fallback
            
        return f"{prefix}{summary}\n\n📄 *Chi tiết:*\n{text[:500]}..."

    async def handle_signal(self, text: str) -> str:
        """
        Xử lý tín hiệu: Trích xuất JSON và format đẹp.
        """
        # 1. AI Extraction
        prompt = f"""
        Bạn là bot trích xuất tín hiệu giao dịch.
        Hãy trích xuất thông tin từ văn bản sau và trả về JSON (không markdown).
        Format: {{"pair": "BTC/USDT", "direction": "LONG/SHORT", "entry": "...", "tp": "...", "sl": "..."}}
        Nếu không tìm thấy thông tin, trả về {{"error": "no_signal"}}
        
        Văn bản:
        {text}
        """
        
        try:
            json_str = await ai_engine.generate_text(prompt)
            # Clean json string (remove markdown code blocks if any)
            json_str = json_str.replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)
            
            if data.get("error"):
                return text # Return original if no signal found
                
            # 2. Format Message
            direction_icon = "🟢" if data.get("direction", "").upper() == "LONG" else "🔴"
            
            formatted_msg = f"""
{direction_icon} **SIGNAL: {data.get('pair', 'Unknown')}**

📈 **Direction:** {data.get('direction')}
🎯 **Entry:** {data.get('entry')}
💰 **TP:** {data.get('tp')}
🛑 **SL:** {data.get('sl')}

📝 *Original:*
{text[:200]}...
"""
            return formatted_msg
            
        except Exception as e:
            logger.warning(f"Failed to extract signal: {e}")
            return text

    async def handle_onchain(self, text: str) -> str:
        """
        Xử lý On-chain: Phân loại Inflow/Outflow.
        """
        text_lower = text.lower()
        prefix = ""
        
        # Simple logic
        if "to binance" in text_lower or "to okx" in text_lower or "to coinbase" in text_lower:
            prefix = "🔴 **INFLOW (Xả)** 📉\n"
        elif "from binance" in text_lower or "from okx" in text_lower or "from coinbase" in text_lower:
            prefix = "🟢 **OUTFLOW (Gom)** 📈\n"
        else:
            prefix = "🔗 **ON-CHAIN ALERT**\n"
            
        return f"{prefix}{text}"

# Singleton instance
strategy_processor = StrategyProcessor()
