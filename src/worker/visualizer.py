from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
from src.common.template_registry import get_template_config
from src.common.logger import logger

class ReportVisualizer:
    def __init__(self):
        # Init Font, Colors
        self.BG_DARK = (20, 25, 40)
        
        # Try to load fonts, fallback to default if not found
        try:
            # Assuming fonts are in assets/fonts or system fonts
            # For now using default or simple path logic
            self.font_title = ImageFont.truetype("arial.ttf", 40)
            self.font_header = ImageFont.truetype("arial.ttf", 30)
            self.font_body = ImageFont.truetype("arial.ttf", 20)
            self.font_bold = ImageFont.truetype("arialbd.ttf", 24)
            self.font_small = ImageFont.truetype("arial.ttf", 16)
        except IOError:
            logger.warning("Custom fonts not found, using default.")
            self.font_title = ImageFont.load_default()
            self.font_header = ImageFont.load_default()
            self.font_body = ImageFont.load_default()
            self.font_bold = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
    
    def _draw_header(self, draw, width, config, title):
        # Vẽ header động theo màu của Template
        theme_color = config.get("theme_color", "#FFFFFF")
        
        # Header Line
        draw.rectangle([0, 0, width, 80], fill=(30, 35, 55))
        draw.line([0, 80, width, 80], fill=theme_color, width=3)
        
        # Title
        draw.text((30, 20), title.upper(), fill=theme_color, font=self.font_title)
        draw.text((width - 200, 30), datetime.now().strftime("%d/%m %H:%M"), fill="#AAAAAA", font=self.font_body)

    def _draw_dynamic_metrics(self, draw, start_y, width, metrics: dict):
        """
        Vẽ các ô thông số động (Grid Layout).
        AI trả về cái gì vẽ cái đó: Volume, Risk, Entry...
        """
        if not metrics: return start_y
        
        draw.text((30, start_y), "KEY METRICS", fill="#FFFFFF", font=self.font_header)
        current_y = start_y + 40
        
        # Chia làm 2 cột
        col_width = (width - 60) // 2
        items = list(metrics.items())
        
        for i, (key, value) in enumerate(items):
            row = i // 2
            col = i % 2
            
            x = 30 + (col * (col_width + 10))
            y = current_y + (row * 70)
            
            # Draw Box
            draw.rectangle([x, y, x + col_width, y + 60], outline="#444455", width=1)
            
            # Label (Key)
            draw.text((x + 10, y + 5), str(key).upper(), fill="#888899", font=self.font_small)
            
            # Value (Tự động đổi màu nếu thấy chữ High/Risk)
            val_str = str(value)
            color = "#00FF00" # Mặc định xanh
            if any(c in val_str.lower() for c in ["high", "sell", "danger", "10/10", "risk"]):
                color = "#FF4500" # Đỏ
            
            draw.text((x + 10, y + 25), val_str, fill=color, font=self.font_bold)
            
        return current_y + ((len(items) + 1) // 2 * 70) + 20

    def _draw_steps_list(self, draw, start_y, steps: list):
        """Vẽ danh sách các bước (cho Airdrop/Tutorial)"""
        draw.text((30, start_y), "ACTION PLAN", fill="#DDA0DD", font=self.font_header)
        y = start_y + 40
        for idx, step in enumerate(steps):
            draw.text((30, y), f"{idx+1}. {step}", fill="#EEEEEE", font=self.font_body)
            y += 35
        return y

    def create_report_image(self, data: dict, template_code: str) -> str:
        config = get_template_config(template_code)
        style = config.get("visual_style", "DEFAULT")
        
        W, H = 800, 1000
        # Nếu là Security Alert, đổi nền sang đỏ đen cho nguy hiểm
        bg_color = (40, 10, 10) if style == "ALERT" else self.BG_DARK
        
        img = Image.new('RGB', (W, H), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # 1. Header
        self._draw_header(draw, W, config, config['name'])
        
        current_y = 120
        
        # 2. Body Customization dựa trên Style
        if style == "ALERT":
            # Vẽ cảnh báo to
            draw.rectangle([30, current_y, W-30, current_y+60], fill="#FF0000")
            draw.text((W//2 - 100, current_y+15), "⚠️ SECURITY WARNING", fill="white", font=self.font_header)
            current_y += 100
            
        # 3. Dynamic Metrics (Đây là phần quan trọng nhất để fix lỗi hardcode)
        # AI trả về metrics gì thì hiển thị cái đó
        metrics = data.get("metrics", {})
        # Fallback nếu AI cũ trả về top_assets
        if "top_assets" in data and not metrics:
             metrics["Assets"] = ", ".join(data["top_assets"])
             
        current_y = self._draw_dynamic_metrics(draw, current_y, W, metrics)
        
        # 4. Content (Summary)
        draw.text((30, current_y), "ANALYSIS", fill=config.get("theme_color"), font=self.font_header)
        summary = data.get("summary", data.get("action_summary", ""))
        
        # Wrap text logic simple
        import textwrap
        lines = textwrap.wrap(summary, width=60) # Approx chars per line
        
        text_y = current_y + 40
        for line in lines[:15]: # Limit lines to prevent overflow
            draw.text((30, text_y), line, fill="white", font=self.font_body)
            text_y += 25
            
        current_y = text_y + 40

        # 5. Specific Sections
        if style == "STEP_LIST" and "steps" in data:
            self._draw_steps_list(draw, current_y, data["steps"])
            
        # Save image
        os.makedirs("temp_images", exist_ok=True)
        filename = f"temp_images/report_{template_code}_{int(datetime.now().timestamp())}.png"
        img.save(filename)
        return filename

visualizer = ReportVisualizer()
