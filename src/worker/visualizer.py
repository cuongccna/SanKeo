from PIL import Image, ImageDraw, ImageFont, ImageColor
from datetime import datetime
import os
import textwrap
from src.common.template_registry import get_template_config
from src.common.logger import logger

class ReportVisualizer:
    def __init__(self):
        # --- PALETTE MÀU TRADER (Professional Dark Theme) ---
        self.COLOR_BG = "#0B0E14"       # Đen xanh thẫm (Binance Dark)
        self.COLOR_CARD = (30, 35, 50, 230) # Màu thẻ (RGBA) - Bán trong suốt
        self.COLOR_GLASS_BORDER = "#2A2F45"
        
        # Signal Colors
        self.COLOR_BULL = "#00C087"     # Xanh lá Crypto
        self.COLOR_BEAR = "#F23645"     # Đỏ nến Nhật
        self.COLOR_NEUTRAL = "#FF9800"  # Vàng cam
        self.COLOR_TEXT_MAIN = "#FFFFFF"
        self.COLOR_TEXT_SUB = "#B2B5BE" # Xám bạc
        self.COLOR_ACCENT = "#2962FF"   # Xanh dương TradingView

        # Font Config
        self.SIZE_TITLE = 60
        self.SIZE_HEADER = 38
        self.SIZE_BODY = 28
        self.SIZE_METRIC_VAL = 42
        self.SIZE_METRIC_LABEL = 22
        
        self._load_fonts()

    def _load_fonts(self):
        """Load font hỗ trợ Tiếng Việt Unicode"""
        # Ưu tiên các font đẹp, hỗ trợ tiếng Việt tốt
        font_candidates = ["Roboto-Bold.ttf", "Arial.ttf", "SegoeUI.ttf", "DejaVuSans.ttf"]
        
        font_paths = [
            ".", 
            "assets/fonts", 
            "C:\\Windows\\Fonts",
            "/usr/share/fonts/truetype/dejavu", 
            "/usr/share/fonts/truetype/liberation",
            "/usr/share/fonts/truetype/freefont"
        ]
        
        found_font = None
        for font_name in font_candidates:
            for path in font_paths:
                full_path = os.path.join(path, font_name)
                if os.path.exists(full_path):
                    found_font = full_path
                    break
            if found_font:
                break
        
        if not found_font:
            found_font = "arial.ttf" # Fallback giả định
        
        try:
            self.font_title = ImageFont.truetype(found_font, self.SIZE_TITLE)
            self.font_header = ImageFont.truetype(found_font, self.SIZE_HEADER)
            self.font_body = ImageFont.truetype(found_font, self.SIZE_BODY)
            self.font_metric_val = ImageFont.truetype(found_font, self.SIZE_METRIC_VAL)
            self.font_metric_lbl = ImageFont.truetype(found_font, self.SIZE_METRIC_LABEL)
            self.font_small = ImageFont.truetype(found_font, 20)
        except:
            self.font_title = ImageFont.load_default()
            self.font_header = ImageFont.load_default()
            self.font_body = ImageFont.load_default()
            self.font_metric_val = ImageFont.load_default()
            self.font_metric_lbl = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    def _draw_glass_card(self, base_img, x, y, w, h, header_text=None, accent_color=None):
        """
        Vẽ thẻ hiệu ứng kính (Glassmorphism) bo góc.
        """
        # Tạo layer riêng để vẽ độ trong suốt
        overlay = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Vẽ nền thẻ bán trong suốt
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=20, fill=self.COLOR_CARD, outline=self.COLOR_GLASS_BORDER, width=2)
        
        # Vẽ Header nhỏ của thẻ (nếu có)
        if header_text:
            # Dải màu tiêu đề
            header_h = 50
            draw.rounded_rectangle([(x, y), (x + w, y + header_h)], radius=20, corners=(True, True, False, False), fill=(40, 45, 65, 255))
            # Đường line màu accent
            line_color = accent_color if accent_color else self.COLOR_ACCENT
            draw.line([(x+20, y+header_h), (x+w-20, y+header_h)], fill=line_color, width=2)
            # Text tiêu đề thẻ
            draw.text((x + 20, y + 12), header_text.upper(), fill=self.COLOR_TEXT_MAIN, font=self.font_small)

        # Gộp layer vào ảnh gốc
        base_img.alpha_composite(overlay)
        return x + 20, y + 60 if header_text else y + 20 # Trả về tọa độ nội dung bên trong

    def _draw_sentiment_bar(self, draw, x, y, width, score):
        """Vẽ thanh đo chỉ số hưng phấn/sợ hãi"""
        # Background bar
        draw.rounded_rectangle([(x, y), (x + width, y + 16)], radius=8, fill="#2C3038")
        
        # Màu sắc dựa trên điểm số
        if score >= 75: fill_color = self.COLOR_BULL
        elif score <= 25: fill_color = self.COLOR_BEAR
        else: fill_color = self.COLOR_NEUTRAL
        
        # Active bar
        bar_w = int(width * (score / 100))
        draw.rounded_rectangle([(x, y), (x + bar_w, y + 16)], radius=8, fill=fill_color)
        
        # Text label
        label = "SỢ HÃI" if score < 40 else ("HƯNG PHẤN" if score > 60 else "TRUNG LẬP")
        draw.text((x + width - 100, y - 30), f"{score}/100 {label}", fill=fill_color, font=self.font_small)

    def _get_trend_color(self, text):
        """Logic xác định màu dựa trên text (Tiếng Việt & Anh)"""
        t = str(text).lower()
        if any(x in t for x in ['mua', 'long', 'buy', 'bull', 'tăng', 'uptrend']):
            return self.COLOR_BULL
        if any(x in t for x in ['bán', 'short', 'sell', 'bear', 'giảm', 'downtrend', 'risk']):
            return self.COLOR_BEAR
        return self.COLOR_TEXT_MAIN

    def _draw_metrics_grid(self, draw, start_x, start_y, width, metrics):
        """Vẽ lưới thông số kỹ thuật (2 cột)"""
        col_w = (width - 40) // 2
        row_h = 80
        
        items = list(metrics.items())
        for i, (k, v) in enumerate(items):
            row = i // 2
            col = i % 2
            
            x = start_x + (col * (col_w + 20))
            y = start_y + (row * (row_h + 15))
            
            # Label (Nhỏ, màu xám)
            draw.text((x, y), str(k).upper(), fill=self.COLOR_TEXT_SUB, font=self.font_metric_lbl)
            
            # Value (Lớn, có màu theo ngữ nghĩa)
            val_color = self._get_trend_color(v)
            draw.text((x, y + 28), str(v), fill=val_color, font=self.font_metric_val)
            
        return start_y + ((len(items) + 1) // 2 * (row_h + 15))

    def create_report_image(self, data: dict, template_code: str) -> str:
        config = get_template_config(template_code)
        
        # 1. Setup Canvas (RGBA để hỗ trợ trong suốt)
        W, H = 1080, 1350 # Tỉ lệ 4:5 chuẩn Instagram/Tele
        img = Image.new('RGBA', (W, H), color=self.COLOR_BG)
        draw = ImageDraw.Draw(img)
        
        # --- HEADER SECTION ---
        # Vẽ dải màu định danh (ví dụ: Tín hiệu = Xanh, Cảnh báo = Đỏ)
        theme_color = config.get("theme_color", self.COLOR_ACCENT)
        draw.rectangle([(0, 0), (W, 15)], fill=theme_color)
        
        # Tiêu đề Template (Tiếng Việt từ Config)
        title_vi = config.get("name_vi", config['name']).upper()
        draw.text((50, 60), title_vi, fill=self.COLOR_TEXT_MAIN, font=self.font_title)
        
        # Ngày giờ
        time_str = datetime.now().strftime("NGÀY %d/%m/%Y | %H:%M")
        draw.text((50, 140), time_str, fill=self.COLOR_TEXT_SUB, font=self.font_small)
        
        # Badge Logo/Bot Name góc phải
        draw.text((W - 250, 70), "SAN KEO BOT AI", fill=self.COLOR_ACCENT, font=self.font_header)

        current_y = 200
        content_width = W - 100 # Margin left/right 50px

        # --- SECTION 1: METRICS (THÔNG SỐ) ---
        metrics = data.get("metrics", {})
        if "top_assets" in data and not metrics:
             metrics["Tài sản"] = ", ".join(data["top_assets"])
        
        if metrics:
            # Vẽ khung Metrics
            inner_x, inner_y = self._draw_glass_card(img, 50, current_y, content_width, 350, "THÔNG SỐ KỸ THUẬT")
            
            # Vẽ lại draw object vì img đã bị thay đổi bởi alpha_composite
            draw = ImageDraw.Draw(img)
            
            # Nếu có Sentiment Score, vẽ thanh bar
            if "score" in data:
                self._draw_sentiment_bar(draw, inner_x, inner_y + 10, content_width - 40, int(data['score']))
                grid_start_y = inner_y + 60
            else:
                grid_start_y = inner_y + 10
                
            self._draw_metrics_grid(draw, inner_x, grid_start_y, content_width - 40, metrics)
            current_y += 380 # Chiều cao card + margin

        # --- SECTION 2: AI ANALYSIS (PHÂN TÍCH) ---
        summary = data.get("summary", data.get("action_summary", ""))
        if summary:
            # Tính chiều cao ước lượng cho text
            lines = textwrap.wrap(summary, width=50) # Width tùy font size
            text_height = len(lines) * 45 + 100
            
            inner_x, inner_y = self._draw_glass_card(img, 50, current_y, content_width, text_height, "NHẬN ĐỊNH CỦA AI", theme_color)
            draw = ImageDraw.Draw(img) # Refresh draw
            
            text_y = inner_y + 20
            for line in lines:
                draw.text((inner_x, text_y), line, fill=self.COLOR_TEXT_MAIN, font=self.font_body)
                text_y += 40
            
            current_y += text_height + 30

        # --- SECTION 3: ACTION PLAN (KHUYẾN NGHỊ) ---
        steps = data.get("steps", [])
        if steps:
            steps_height = len(steps) * 60 + 100
            inner_x, inner_y = self._draw_glass_card(img, 50, current_y, content_width, steps_height, "HÀNH ĐỘNG KHUYẾN NGHỊ", "#DDA0DD")
            draw = ImageDraw.Draw(img)
            
            step_y = inner_y + 20
            for idx, step in enumerate(steps):
                # Vẽ số thứ tự tròn
                draw.ellipse([(inner_x, step_y), (inner_x+30, step_y+30)], fill=self.COLOR_ACCENT)
                draw.text((inner_x+10, step_y+4), str(idx+1), fill="white", font=self.font_small)
                
                # Text
                draw.text((inner_x + 50, step_y), step, fill=self.COLOR_TEXT_MAIN, font=self.font_body)
                step_y += 50

        # --- FOOTER ---
        draw.line([(50, H - 80), (W - 50, H - 80)], fill="#2A2F45", width=2)
        draw.text((50, H - 60), "⚠️ Cảnh báo: Thị trường Crypto có rủi ro cao. DYOR.", fill=self.COLOR_TEXT_SUB, font=self.font_small)

        # Convert back to RGB to save as JPG/PNG without alpha issues if needed
        final_img = img.convert("RGB")
        
        # Save
        os.makedirs("temp_images", exist_ok=True)
        filename = f"temp_images/report_{template_code}_{int(datetime.now().timestamp())}.jpg"
        final_img.save(filename, quality=95)
        logger.info(f"Generated glassy report: {filename}")
        return filename

visualizer = ReportVisualizer()
