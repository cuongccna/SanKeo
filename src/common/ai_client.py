import google.generativeai as genai
from src.common.config import settings
from src.common.logger import logger

class AIClient:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set. AI analysis will be disabled.")
            self.model = None
            return

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
            logger.info(f"AI Client initialized with model: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize AI Client: {e}")
            self.model = None

    async def generate_template_report(self, messages: list, template_type: str) -> str:
        if not self.model:
            return "AI Service Unavailable"

        # Format messages for the prompt
        messages_text = "\n".join([f"- {msg}" for msg in messages])

        prompt = f"""
        Bạn là một chuyên gia phân tích thị trường Crypto. Nhiệm vụ của bạn là tổng hợp các mẩu tin rời rạc sau đây thành một báo cáo {template_type} súc tích.

        Dữ liệu đầu vào:
        {messages_text}

        Yêu cầu:
        - Tìm mối liên hệ giữa các tin (Ví dụ: Onchain báo gom + Tin tức tốt -> Kết luận Bullish).
        - Đưa ra nhận định xu hướng ngắn hạn.
        - BẮT BUỘC: Cuối báo cáo phải có dòng: "⚠️ <i>Nhận định được tổng hợp bởi AI từ các nguồn tin trên, chỉ mang tính tham khảo, không phải lời khuyên đầu tư.</i>"
        - Không xưng là "tôi" hay "AI", hãy dùng giọng văn khách quan của một bản báo cáo tài chính.
        
        QUAN TRỌNG VỀ ĐỊNH DẠNG (Telegram HTML):
        1. CHỈ sử dụng các thẻ: <b>, <i>, <u>, <s>, <a>, <code>, <pre>.
        2. TUYỆT ĐỐI KHÔNG sử dụng: <p>, <ul>, <li>, <h1>, <h2>, <br>, <div>.
        3. TUYỆT ĐỐI KHÔNG bao quanh nội dung bằng ```html hoặc ```. Trả về text thô chứa thẻ HTML.
        4. Xuống dòng: Sử dụng phím Enter (ký tự xuống dòng thực tế), không dùng thẻ <br> hay <p>.
        5. Danh sách: Sử dụng gạch đầu dòng (-) hoặc emoji (•, 🔹) thay cho thẻ <ul>/<li>.
        """

        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Clean up markdown code blocks if AI ignores instructions
            if text.startswith("```html"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            return text.strip()
        except Exception as e:
            logger.error(f"AI Template Generation failed: {e}")
            return "AI Generation Failed"

ai_client = AIClient()
