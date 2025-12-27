"""
VISUALIZER - HTML to Image Report Generator
Sử dụng Playwright để render HTML template thành hình ảnh PNG chất lượng cao.
"""
import os
import asyncio
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from src.common.template_registry import get_template_config
from src.common.logger import logger

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"

class ReportVisualizer:
    def __init__(self):
        self.browser = None
        self.playwright = None
        self._lock = asyncio.Lock()
        
        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True
        )
        
        # Register custom filter (not global function)
        self.jinja_env.filters['trend_class'] = self._get_trend_class
        
        # Load CSS once
        css_path = TEMPLATE_DIR / "styles.css"
        if css_path.exists():
            self.css_content = css_path.read_text(encoding='utf-8')
        else:
            self.css_content = ""
            logger.warning("CSS file not found!")
    
    async def _ensure_browser(self):
        """Lazy initialization of browser (singleton pattern)."""
        if self.browser is None:
            async with self._lock:
                if self.browser is None:
                    try:
                        from playwright.async_api import async_playwright
                        self.playwright = await async_playwright().start()
                        self.browser = await self.playwright.chromium.launch(
                            headless=True,
                            args=['--no-sandbox', '--disable-setuid-sandbox']
                        )
                        logger.info("Playwright browser initialized successfully.")
                    except Exception as e:
                        logger.error(f"Failed to initialize Playwright: {e}")
                        raise
        return self.browser
    
    def _get_trend_class(self, text: str) -> str:
        """Xác định CSS class dựa trên nội dung text."""
        if not text:
            return ""
        t = str(text).lower()
        if any(x in t for x in ['mua', 'long', 'buy', 'bull', 'tăng', 'uptrend', 'mạnh', 'tích cực']):
            return "bull"
        if any(x in t for x in ['bán', 'short', 'sell', 'bear', 'giảm', 'downtrend', 'risk', 'yếu', 'tiêu cực']):
            return "bear"
        return ""
    
    def _get_score_info(self, score: int) -> tuple:
        """Trả về (class, label) dựa trên điểm số."""
        if score >= 60:
            return ("bull", "HƯNG PHẤN")
        elif score <= 40:
            return ("bear", "SỢ HÃI")
        else:
            return ("neutral", "TRUNG LẬP")
    
    def _render_html(self, data: dict, template_code: str) -> str:
        """Render data thành HTML string."""
        config = get_template_config(template_code)
        
        # Get score info
        score = data.get("score")
        score_class, score_label = "", ""
        if score is not None:
            score_class, score_label = self._get_score_info(int(score))
        
        # Prepare context
        context = {
            "title": config.get("name_vi", config.get("name", "BÁO CÁO")),
            "theme_color": config.get("theme_color", "#2962FF"),
            "timestamp": datetime.now().strftime("%d/%m/%Y | %H:%M"),
            "css": self.css_content,
            "metrics": data.get("metrics", {}),
            "summary": data.get("summary", data.get("action_summary", "")),
            "steps": data.get("steps", []),
            "score": score,
            "score_class": score_class,
            "score_label": score_label,
        }
        
        # Render template
        template = self.jinja_env.get_template("report.html")
        return template.render(**context)
    
    async def create_report_image(self, data: dict, template_code: str) -> str:
        """
        Tạo hình ảnh báo cáo từ dữ liệu.
        Returns: Đường dẫn đến file hình ảnh.
        """
        try:
            # Render HTML
            html_content = self._render_html(data, template_code)
            
            # Ensure browser is ready
            browser = await self._ensure_browser()
            
            # Create new page
            page = await browser.new_page(
                viewport={'width': 540, 'height': 800},
                device_scale_factor=2  # Retina quality
            )
            
            try:
                # Set content
                await page.set_content(html_content, wait_until='networkidle')
                
                # Get actual content height
                content_height = await page.evaluate('''() => {
                    const container = document.querySelector('.report-container');
                    return container ? container.offsetHeight : 800;
                }''')
                
                # Resize viewport to fit content
                await page.set_viewport_size({'width': 540, 'height': content_height})
                
                # Ensure output directory exists
                os.makedirs("temp_images", exist_ok=True)
                
                # Generate filename
                filename = f"temp_images/report_{template_code}_{int(datetime.now().timestamp())}.png"
                
                # Take screenshot
                await page.screenshot(
                    path=filename,
                    type='png',
                    clip={'x': 0, 'y': 0, 'width': 540, 'height': content_height}
                )
                
                logger.info(f"Generated HTML report: {filename}")
                return filename
                
            finally:
                await page.close()
                
        except Exception as e:
            logger.error(f"Failed to create report image: {e}")
            # Fallback: Return None or create a simple error image
            return await self._create_fallback_image(data, template_code, str(e))
    
    async def _create_fallback_image(self, data: dict, template_code: str, error: str) -> str:
        """Tạo ảnh fallback khi Playwright lỗi (dùng PIL cơ bản)."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            W, H = 540, 400
            img = Image.new('RGB', (W, H), color='#0B0E14')
            draw = ImageDraw.Draw(img)
            
            # Try to load font
            try:
                font = ImageFont.truetype("arial.ttf", 20)
                font_small = ImageFont.truetype("arial.ttf", 14)
            except:
                font = ImageFont.load_default()
                font_small = font
            
            # Draw basic info
            config = get_template_config(template_code)
            title = config.get("name_vi", "BÁO CÁO")
            
            draw.text((30, 30), title, fill='#FFFFFF', font=font)
            draw.text((30, 70), f"Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M')}", fill='#B2B5BE', font=font_small)
            
            # Summary
            summary = data.get("summary", "Không có dữ liệu")[:200]
            y = 110
            for line in summary.split('\n')[:5]:
                draw.text((30, y), line[:60], fill='#FFFFFF', font=font_small)
                y += 25
            
            # Error note (for debugging)
            draw.text((30, H - 40), f"[Fallback mode: {error[:50]}]", fill='#F23645', font=font_small)
            
            os.makedirs("temp_images", exist_ok=True)
            filename = f"temp_images/report_{template_code}_{int(datetime.now().timestamp())}_fallback.png"
            img.save(filename)
            logger.warning(f"Created fallback image: {filename}")
            return filename
            
        except Exception as e2:
            logger.error(f"Even fallback failed: {e2}")
            return None
    
    async def close(self):
        """Cleanup browser resources."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        logger.info("Playwright browser closed.")


# Singleton instance
visualizer = ReportVisualizer()
