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
        - ĐỊNH DẠNG: Sử dụng thẻ HTML để định dạng văn bản (Telegram HTML style):
          + In đậm: <b>Nội dung</b> (Dùng cho tiêu đề, điểm nhấn)
          + In nghiêng: <i>Nội dung</i>
          + KHÔNG dùng Markdown (như **, ##, __). Chỉ dùng HTML.
        """

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI Template Generation failed: {e}")
            return "AI Generation Failed"

ai_client = AIClient()
