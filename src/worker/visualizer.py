from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
import textwrap
from src.common.template_registry import get_template_config
from src.common.logger import logger

class ReportVisualizer:
    def __init__(self):
        # Init Colors
        self.BG_DARK = (15, 20, 35) # Darker, cleaner blue-black
        self.ACCENT_COLOR = (0, 255, 200) # Cyan accent
        self.TEXT_MAIN = (255, 255, 255)
        self.TEXT_SUB = (180, 180, 190)
        
        # Font Sizes (High Res)
        self.SIZE_TITLE = 70
        self.SIZE_HEADER = 45
        self.SIZE_BODY = 32
        self.SIZE_BOLD = 36
        self.SIZE_SMALL = 24
        
        self._load_fonts()
        
    def _load_fonts(self):
        """Robust font loading for Windows/Linux"""
        font_candidates = [
            "arial.ttf", 
            "SegoeUI.ttf", 
            "Roboto-Regular.ttf", 
            "DejaVuSans.ttf", 
            "LiberationSans-Regular.ttf",
            "FreeSans.ttf"
        ]
        
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
            if found_font: break
            
        # Fallback to just filename (system path)
        if not found_font:
            found_font = "arial.ttf"

        try:
            self.font_title = ImageFont.truetype(found_font, self.SIZE_TITLE)
            self.font_header = ImageFont.truetype(found_font, self.SIZE_HEADER)
            self.font_body = ImageFont.truetype(found_font, self.SIZE_BODY)
            self.font_bold = ImageFont.truetype(found_font, self.SIZE_BOLD)
            self.font_small = ImageFont.truetype(found_font, self.SIZE_SMALL)
            logger.info(f"Loaded font: {found_font}")
        except IOError:
            logger.warning("Custom fonts not found, using default (UGLY).")
            self.font_title = ImageFont.load_default()
            self.font_header = ImageFont.load_default()
            self.font_body = ImageFont.load_default()
            self.font_bold = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
    
    def _draw_header(self, draw, width, config, title):
        theme_color = config.get("theme_color", "#FFFFFF")
        
        # Header Background
        draw.rectangle([0, 0, width, 140], fill=(25, 30, 50))
        
        # Accent Line
        draw.line([0, 138, width, 138], fill=theme_color, width=6)
        
        # Title (Centered or Left)
        draw.text((40, 35), title.upper(), fill=theme_color, font=self.font_title)
        
        # Timestamp
        time_str = datetime.now().strftime("%d/%m %H:%M")
        # Calculate text width roughly or just align right
        draw.text((width - 280, 55), time_str, fill=self.TEXT_SUB, font=self.font_small)

    def _draw_dynamic_metrics(self, draw, start_y, width, metrics: dict):
        if not metrics: return start_y
        
        # Section Title
        draw.text((40, start_y), "KEY METRICS", fill=self.ACCENT_COLOR, font=self.font_header)
        current_y = start_y + 60
        
        # Grid Layout
        col_width = (width - 100) // 2
        row_height = 100
        items = list(metrics.items())
        
        for i, (key, value) in enumerate(items):
            row = i // 2
            col = i % 2
            
            x = 40 + (col * (col_width + 20))
            y = current_y + (row * (row_height + 20))
            
            # Draw Box Background
            draw.rectangle([x, y, x + col_width, y + row_height], fill=(30, 35, 55), outline=(60, 70, 90), width=2)
            
            # Label (Key) - Top Left
            draw.text((x + 20, y + 15), str(key).upper(), fill=self.TEXT_SUB, font=self.font_small)
            
            # Value - Center/Bottom
            val_str = str(value)
            
            # Color Logic
            color = "#00FF7F" # SpringGreen
            val_lower = val_str.lower()
            if any(c in val_lower for c in ["high", "sell", "danger", "risk", "scam", "down"]):
                color = "#FF4500" # OrangeRed
            elif any(c in val_lower for c in ["medium", "neutral"]):
                color = "#FFD700" # Gold
            
            # Simple centering logic (approximate)
            # Assuming ~15px per char for bold font
            text_width = len(val_str) * 18 
            text_x = x + 20
            
            draw.text((text_x, y + 45), val_str, fill=color, font=self.font_bold)
            
        rows = (len(items) + 1) // 2
        return current_y + (rows * (row_height + 20)) + 40

    def _draw_steps_list(self, draw, start_y, steps: list):
        draw.text((40, start_y), "ACTION PLAN", fill="#DDA0DD", font=self.font_header)
        y = start_y + 60
        for idx, step in enumerate(steps):
            # Wrap step text
            lines = textwrap.wrap(step, width=50)
            for line in lines:
                draw.text((40, y), f"{idx+1}. {line}" if line == lines[0] else f"   {line}", fill=self.TEXT_MAIN, font=self.font_body)
                y += 45
            y += 15 # Extra space between steps
        return y

    def create_report_image(self, data: dict, template_code: str) -> str:
        config = get_template_config(template_code)
        style = config.get("visual_style", "DEFAULT")
        
        # High Resolution Canvas
        W, H = 1080, 1440 
        
        # Background Color
        bg_color = (40, 10, 10) if style == "ALERT" else self.BG_DARK
        
        img = Image.new('RGB', (W, H), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # 1. Header
        self._draw_header(draw, W, config, config['name'])
        
        current_y = 180
        
        # 2. Alert Banner
        if style == "ALERT":
            draw.rectangle([40, current_y, W-40, current_y+100], fill="#8B0000")
            draw.text((W//2 - 200, current_y+25), "⚠️ SECURITY WARNING", fill="white", font=self.font_header)
            current_y += 140
            
        # 3. Metrics
        metrics = data.get("metrics", {})
        if "top_assets" in data and not metrics:
             metrics["Assets"] = ", ".join(data["top_assets"])
             
        current_y = self._draw_dynamic_metrics(draw, current_y, W, metrics)
        
        # 4. Analysis / Summary
        draw.text((40, current_y), "ANALYSIS", fill=config.get("theme_color"), font=self.font_header)
        current_y += 60
        
        summary = data.get("summary", data.get("action_summary", ""))
        
        # Text Wrapping
        # Width 1080px, font size 32px (~16px width avg) -> ~60 chars
        lines = textwrap.wrap(summary, width=55)
        
        for line in lines[:20]: # Limit to avoid overflow
            draw.text((40, current_y), line, fill=self.TEXT_MAIN, font=self.font_body)
            current_y += 45
            
        current_y += 40

        # 5. Steps (if any)
        if style == "STEP_LIST" and "steps" in data:
            self._draw_steps_list(draw, current_y, data["steps"])
            
        # 6. Footer
        draw.line([40, H-60, W-40, H-60], fill=(60, 70, 90), width=2)
        draw.text((W//2 - 100, H-45), "SanKeo Bot AI", fill=self.TEXT_SUB, font=self.font_small)

        # Save
        os.makedirs("temp_images", exist_ok=True)
        filename = f"temp_images/report_{template_code}_{int(datetime.now().timestamp())}.png"
        img.save(filename)
        logger.info(f"Generated report image: {filename}")
        return filename

visualizer = ReportVisualizer()
