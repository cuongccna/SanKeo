import re
import hashlib
from typing import List, Optional, Set
from pydantic import BaseModel, Field
from cachetools import TTLCache

class FilterRule(BaseModel):
    """
    Định nghĩa cấu trúc một luật lọc.
    """
    id: int
    user_id: int
    must_have: List[str] = Field(default_factory=list, description="Danh sách từ khóa BẮT BUỘC phải có (OR logic)")
    must_not_have: List[str] = Field(default_factory=list, description="Danh sách từ khóa KHÔNG được có")
    source_channels: Optional[List[int]] = Field(None, description="Chỉ lọc từ các channel ID này (None = tất cả)")

class MessageProcessor:
    """
    Core logic xử lý và lọc tin nhắn.
    """
    def __init__(self, dedup_ttl: int = 300, dedup_maxsize: int = 10000):
        # Cache lưu hash của tin nhắn để chống spam/duplicate. 
        # TTL = 300s (5 phút), Max size = 10000 tin nhắn.
        self._dedup_cache = TTLCache(maxsize=dedup_maxsize, ttl=dedup_ttl)

    def normalize_text(self, text: str) -> str:
        """
        Chuẩn hóa văn bản:
        - Chuyển về lowercase.
        - Giữ lại chữ cái, số, khoảng trắng và các ký tự quan trọng cho crypto ($, #, @).
        - Xóa các ký tự đặc biệt khác gây nhiễu.
        """
        if not text:
            return ""
        
        text = text.lower()
        # Giữ lại a-z, 0-9, khoảng trắng, $, #, @, ., -
        # Thay thế các ký tự khác bằng khoảng trắng để tránh dính từ
        text = re.sub(r'[^a-z0-9\s$#@.-]', ' ', text)
        # Xóa khoảng trắng thừa
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _generate_hash(self, text: str) -> str:
        """Tạo hash MD5 cho text để check trùng."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def is_duplicate(self, text: str) -> bool:
        """
        Kiểm tra xem nội dung tin nhắn đã được xử lý gần đây chưa.
        """
        msg_hash = self._generate_hash(text)
        if msg_hash in self._dedup_cache:
            return True
        self._dedup_cache[msg_hash] = True
        return False

    def check_keywords(self, normalized_text: str, rule: FilterRule) -> bool:
        """
        Kiểm tra text có khớp với rule không.
        Logic: (Có ít nhất 1 từ trong must_have) AND (Không có từ nào trong must_not_have)
        """
        # 1. Check Must Not Have (Fail fast)
        for keyword in rule.must_not_have:
            # Dùng \b để bắt chính xác từ (word boundary), tránh match nhầm (ví dụ "bit" trong "bitcoin")
            # Escape keyword để an toàn với regex
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, normalized_text):
                return False

        # 2. Check Must Have
        if not rule.must_have:
            return True # Nếu không có điều kiện must_have, coi như pass (hoặc tùy logic nghiệp vụ)

        for keyword in rule.must_have:
            # Hỗ trợ Regex trong keyword nếu người dùng nhập (ví dụ: "eth|btc")
            # Tuy nhiên ở mức cơ bản, ta giả sử keyword là plain text.
            # Nếu muốn hỗ trợ regex từ user, cần try-catch re.error.
            
            # Ở đây ta dùng simple regex search với word boundary
            try:
                # Nếu keyword chứa ký tự đặc biệt regex, ta coi như user muốn dùng regex
                if any(c in keyword for c in r".^$*+?{}[]\|()"):
                     if re.search(keyword, normalized_text):
                         return True
                else:
                    # Keyword thường -> match chính xác từ
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, normalized_text):
                        return True
            except re.error:
                # Fallback nếu regex lỗi: tìm string thường
                if keyword in normalized_text:
                    return True

        return False

    def process_incoming_message(self, raw_message: dict, user_rules_list: List[FilterRule]) -> List[FilterRule]:
        """
        Xử lý luồng chính cho một tin nhắn.
        Trả về danh sách các Rule khớp (để Bot biết gửi cho ai).
        """
        raw_text = raw_message.get("text", "")
        chat_id = raw_message.get("chat_id")

        if not raw_text:
            return []

        # 1. Chuẩn hóa
        normalized_text = self.normalize_text(raw_text)

        # 2. Check trùng (Global deduplication cho nội dung)
        # Lưu ý: Nếu muốn user A nhận được dù user B đã nhận tin giống hệt, 
        # thì logic dedup này cần đặt sau hoặc điều chỉnh scope.
        # Ở đây ta dedup global để tiết kiệm resource: 1 tin rác chỉ xử lý 1 lần.
        if self.is_duplicate(normalized_text):
            return []

        matched_rules = []

        # 3. Loop qua Rules
        for rule in user_rules_list:
            # Check source channel (nếu rule có quy định)
            if rule.source_channels and chat_id not in rule.source_channels:
                continue

            # Check keywords
            if self.check_keywords(normalized_text, rule):
                matched_rules.append(rule)

        return matched_rules
