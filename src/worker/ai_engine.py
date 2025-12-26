import google.generativeai as genai
import PIL.Image
import json
import logging
from datetime import datetime
import pytz # Cần pip install pytz
from src.common.config import settings
from src.common.logger import logger
from src.common.template_registry import get_template_config

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

    async def generate_structured_report(self, messages: list, template_code: str) -> dict:
        """
        Tạo báo cáo có cấu trúc (JSON) cho Visualizer.
        Tích hợp: Time Context + Strict JSON enforcement.
        """
        if not self.model:
            return None
            
        config = get_template_config(template_code)
        
        # 1. Lấy thời gian thực (Việt Nam)
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        # 2. Context từ tin nhắn
        # Giới hạn context window để tránh quá tải token, lấy 50 tin mới nhất
        context_text = "\n---\n".join(messages[:50])
        
        # 3. Dynamic Prompt (Đã nâng cấp với Time Context & Anti-Hallucination)
        system_prompt = f"""
        {config['ai_prompt']}
        
        --- BỐI CẢNH THỜI GIAN THỰC (QUAN TRỌNG) ---
        🕒 THỜI GIAN HIỆN TẠI (VN): {now_str}
        
        LUẬT BẮT BUỘC:
        1. KIỂM TRA THỜI GIAN: So sánh thời gian trong tin nhắn với "THỜI GIAN HIỆN TẠI". 
           - Nếu tin nhắn nói "hôm qua" hoặc quá 24h, hãy coi là tin cũ (trừ khi là phân tích vĩ mô).
           - Ưu tiên tin nhắn mới nhất.
        2. CHỐNG BỊA ĐẶT (HALLUCINATION): 
           - Chỉ trích xuất con số (Giá, Volume) có trong văn bản. KHÔNG ĐƯỢC ĐOÁN.
           - Nếu không có dữ liệu, trả về "N/A" hoặc null.
        3. OUTPUT JSON THUẦN: 
           - Trả về JSON hợp lệ. Không dùng Markdown (```json). Không giải thích thêm.
           - Field "metrics" phải luôn tồn tại (dù rỗng).
        
        Dữ liệu đầu vào (Tin nhắn Telegram):
        {context_text}
        """

        try:
            # Tăng temperature lên một chút (0.4) để AI linh hoạt hơn trong việc tóm tắt, 
            # nhưng vẫn đủ thấp để giữ cấu trúc JSON.
            generation_config = genai.types.GenerationConfig(
                temperature=0.4,
                response_mime_type="application/json" # Ép Gemini trả về JSON Mode (tính năng mới)
            )

            response = await self.model.generate_content_async(
                system_prompt, 
                generation_config=generation_config
            )
            
            raw_text = response.text.strip()
            
            # --- Robust JSON Parsing ---
            # Xử lý trường hợp AI vẫn cố tình trả về Markdown code block
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            data = json.loads(raw_text.strip())
            
            # Handle case where AI returns a list instead of a dict
            if isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    data = data[0]
                else:
                    data = {"summary": str(data), "metrics": {}}

            # Đảm bảo cấu trúc dữ liệu cho Visualizer
            if "metrics" not in data: 
                data["metrics"] = {}
            
            # Tự động tính toán/điền các field bị thiếu để Visualizer không lỗi
            if "score" not in data:
                data["score"] = 50 # Default neutral
            if "summary" not in data:
                data["summary"] = "Không đủ dữ liệu để tóm tắt."

            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"AI JSON Decode Error for {template_code}: {e} | Raw: {raw_text[:100]}...")
            return None
        except Exception as e:
            logger.error(f"AI Error for {template_code}: {e}")
            return None

    async def generate_text(self, prompt: str) -> str:
        """
        Generic method to generate text (dùng cho các task phụ).
        """
        if not self.model: return ""
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI Generation failed: {e}")
            return ""

    async def analyze_message(self, message_text: str, plan_type: str = "VIP") -> str:
        """
        Phân tích nhanh 1 tin nhắn lẻ (Dùng cho Bot chat trực tiếp).
        """
        if not self.model: return "AI Analysis Unavailable"

        if plan_type == "BUSINESS":
            prompt = f"""
            Bạn là chuyên gia Crypto Alpha Hunter. Phân tích tin nhắn sau:
            "{message_text}"
            
            Output Format Telegram:
            📌 **Tóm tắt**: ...
            📊 **Phân tích**: ...
            🎯 **Vùng giá**: Entry/TP (nếu có)
            ⭐ **Điểm**: 1-10
            💡 **Chiến lược**: ...
            """
        else:
            prompt = f"""
            Phân tích tin nhắn Crypto sau ngắn gọn:
            "{message_text}"
            
            Output:
            - Tóm tắt: ...
            - Đánh giá: 1-10
            - Hành động: Mua/Bán/Quan sát
            """

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI Analysis failed: {e}")
            return "AI Analysis Failed"

    async def extract_text_from_image(self, image_path: str) -> str:
        """
        OCR ảnh chart/kèo (Dùng cho Ingestor).
        """
        if not self.model: return ""
        try:
            img = PIL.Image.open(image_path)
            prompt = "Extract details: Token, Entry, TP, SL, Direction (Long/Short). Return just text."
            response = await self.model.generate_content_async([prompt, img])
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI OCR failed: {e}")
            return ""

ai_engine = AIEngine()
