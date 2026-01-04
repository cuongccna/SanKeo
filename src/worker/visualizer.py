"""
VISUALIZER - Text Report Formatter
Chuyển đổi dữ liệu AI thành báo cáo text đẹp mắt cho Telegram.
"""
from datetime import datetime
from src.common.template_registry import get_template_config
from src.common.logger import logger


class ReportVisualizer:
    def __init__(self):
        pass
    
    def _get_trend_emoji(self, text: str) -> str:
        """Xác định emoji dựa trên nội dung text."""
        if not text:
            return ""
        t = str(text).lower()
        if any(x in t for x in ['mua', 'long', 'buy', 'bull', 'tăng', 'uptrend', 'mạnh', 'tích cực']):
            return "🟢"
        if any(x in t for x in ['bán', 'short', 'sell', 'bear', 'giảm', 'downtrend', 'risk', 'yếu', 'tiêu cực']):
            return "🔴"
        return "⚪"
    
    def _get_score_info(self, score: int) -> tuple:
        """Trả về (emoji, label) dựa trên điểm số."""
        if score >= 70:
            return ("🟢", "HƯNG PHẤN")
        elif score >= 60:
            return ("🟡", "LẠC QUAN")
        elif score <= 30:
            return ("🔴", "SỢ HÃI")
        elif score <= 40:
            return ("🟠", "THẬN TRỌNG")
        else:
            return ("⚪", "TRUNG LẬP")
    
    def _build_score_bar(self, score: int) -> str:
        """Tạo thanh tiến trình dạng text."""
        filled = int(score / 10)
        empty = 10 - filled
        
        if score >= 60:
            bar_char = "█"
        elif score <= 40:
            bar_char = "▓"
        else:
            bar_char = "▒"
            
        return f"[{bar_char * filled}{'░' * empty}]"
    
    def format_text_report(self, data: dict, template_code: str) -> str:
        """
        Format dữ liệu thành báo cáo text cho Telegram.
        Returns: Chuỗi text báo cáo đã format.
        """
        try:
            config = get_template_config(template_code)
            
            # Header
            title = config.get("name_vi", config.get("name", "BÁO CÁO"))
            theme_emoji = config.get("emoji", "📊")
            timestamp = datetime.now().strftime("%d/%m/%Y | %H:%M")
            
            lines = []
            lines.append(f"{theme_emoji} <b>{title}</b>")
            lines.append(f"🕒 {timestamp}")
            lines.append("━" * 28)
            
            # Score section
            score = data.get("score")
            if score is not None:
                score = int(score)
                emoji, label = self._get_score_info(score)
                bar = self._build_score_bar(score)
                lines.append(f"\n{emoji} <b>CHỈ SỐ TÂM LÝ: {score}/100</b>")
                lines.append(f"<code>{bar}</code> {label}")
            
            # Metrics section
            metrics = data.get("metrics", {})
            if metrics:
                lines.append(f"\n📈 <b>THÔNG SỐ KỸ THUẬT</b>")
                lines.append("─" * 25)
                for key, value in metrics.items():
                    trend_emoji = self._get_trend_emoji(str(value))
                    lines.append(f"• <b>{key}</b>: {value} {trend_emoji}")
            
            # Summary section
            summary = data.get("summary", data.get("action_summary", ""))
            if summary:
                lines.append(f"\n🤖 <b>NHẬN ĐỊNH CỦA AI</b>")
                lines.append("─" * 25)
                lines.append(f"{summary}")
            
            # Steps/Actions section
            steps = data.get("steps", [])
            if steps:
                lines.append(f"\n🎯 <b>HÀNH ĐỘNG KHUYẾN NGHỊ</b>")
                lines.append("─" * 25)
                for i, step in enumerate(steps, 1):
                    lines.append(f"{i}. {step}")
            
            # Footer
            lines.append("\n" + "━" * 28)
            lines.append("⚠️ <i>Thị trường Crypto có rủi ro cao. DYOR.</i>")
            lines.append("🔗 <b>SAN KEO BOT AI</b>")
            
            report_text = "\n".join(lines)
            logger.info(f"Generated text report for {template_code}")
            return report_text
            
        except Exception as e:
            logger.error(f"Failed to format text report: {e}")
            return self._create_fallback_report(data, template_code)
    
    def _create_fallback_report(self, data: dict, template_code: str) -> str:
        """Tạo báo cáo fallback khi format lỗi."""
        config = get_template_config(template_code)
        title = config.get("name_vi", "BÁO CÁO")
        summary = data.get("summary", "Không có dữ liệu")
        
        return f"""
📊 <b>{title}</b>
🕒 {datetime.now().strftime("%d/%m/%Y %H:%M")}
━━━━━━━━━━━━━━━━━━━━━━━━━━━
{summary}
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Thị trường Crypto có rủi ro cao. DYOR.</i>
"""


# Singleton instance
visualizer = ReportVisualizer()
