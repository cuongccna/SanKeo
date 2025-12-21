import google.generativeai as genai
import PIL.Image
from src.common.config import settings
from src.common.logger import logger

class AIEngine:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set. AI analysis will be disabled.")
            self.model = None
            return

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
            logger.info(f"AI Engine initialized with model: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize AI Engine: {e}")
            self.model = None

    async def generate_text(self, prompt: str) -> str:
        """
        Generic method to generate text from prompt.
        """
        if not self.model:
            return ""
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI Generation failed: {e}")
            return ""

    async def analyze_message(self, message_text: str, plan_type: str = "VIP") -> str:
        if not self.model:
            return "AI Analysis Unavailable (Missing Key)"

        if plan_type == "BUSINESS":
            prompt = f"""
            Bạn là một chuyên gia phân tích thị trường Crypto (Alpha Hunter) cao cấp.
            Hãy phân tích tin nhắn sau một cách chi tiết, tập trung vào xu hướng, tâm lý và dòng tiền.
            
            Tin nhắn:
            {message_text}
            
            Yêu cầu đầu ra (Format Telegram, không dùng code block):
            
            📌 **Tóm tắt**: [Nội dung chính]
            
            📊 **Phân tích**: [Đánh giá setup, rủi ro, tiềm năng]
            
            🧠 **Tâm lý & Onchain**: [Phân tích tâm lý đám đông, dòng tiền, hành động cá mập]
            
            🎯 **Vùng giá quan tâm**: [Entry/TP nếu có, không đưa ra SL cụ thể]
            
            ⭐ **Đánh giá**: [Thang điểm 1-10]
            
            💡 **Chiến lược**: [Ngắn hạn/Dài hạn, Quản lý vốn]
            
            _⚠️ Nhận định được hỗ trợ bởi AI, chỉ mang tính tham khảo. Không phải lời khuyên đầu tư._
            
            Lưu ý: 
            - Không dùng header "AI Analysis".
            - Trình bày thoáng, dễ đọc.
            - Ngắn gọn, súc tích.
            """
        else:
            # VIP (Basic)
            prompt = f"""
            Bạn là một chuyên gia phân tích tín hiệu Crypto (Alpha Hunter).
            Hãy phân tích tin nhắn sau và đưa ra đánh giá ngắn gọn (tối đa 5 dòng).
            
            Tin nhắn:
            {message_text}
            
            Yêu cầu đầu ra:
            - Tóm tắt: [Nội dung chính]
            - Đánh giá: [Thang điểm 1-10]
            - Hành động: [Mua/Bán/Quan sát]
            
            Nếu tin nhắn là spam hoặc không phải tín hiệu, hãy trả về "Spam/Irrelevant".
            """

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI Analysis failed: {e}")
            return "AI Analysis Failed"

    async def extract_text_from_image(self, image_path: str) -> str:
        if not self.model:
            return ""
        
        try:
            img = PIL.Image.open(image_path)
            prompt = "Extract all text from this image. If it contains a chart or signal, describe the key details (Token, Entry, TP, SL)."
            response = await self.model.generate_content_async([prompt, img])
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI OCR failed: {e}")
            return ""

ai_engine = AIEngine()
