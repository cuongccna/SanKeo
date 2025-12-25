import re
import hashlib
from typing import List, Optional, Set, Pattern
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

    # Cache pre-compiled regex để tăng tốc độ (Không lưu vào DB, chỉ dùng runtime)
    _compiled_must_have: List[Pattern] = []
    _compiled_must_not_have: List[Pattern] = []

    def __init__(self, **data):
        super().__init__(**data)
        self._compile_patterns()

    def _compile_patterns(self):
        """
        Compile regex trước để không phải làm việc này mỗi khi có tin nhắn mới.
        """
        self._compiled_must_have = [self._create_regex(k) for k in self.must_have]
        self._compiled_must_not_have = [self._create_regex(k) for k in self.must_not_have]

    def _create_regex(self, keyword: str) -> Pattern:
        """
        Tạo regex thông minh:
        - Xử lý đúng boundary cho từ thường và từ có ký tự đặc biệt ($BTC).
        - Hỗ trợ user nhập regex trực tiếp nếu muốn.
        """
        # Nếu user cố tình nhập regex phức tạp (có chứa . * + ? ...)
        is_user_regex = any(c in keyword for c in r".^*+?{}[]\|()")
        
        if is_user_regex:
            try:
                return re.compile(keyword, re.IGNORECASE)
            except re.error:
                # Fallback về text thường nếu regex lỗi
                pass

        escaped_kw = re.escape(keyword)
        
        # LOGIC QUAN TRỌNG:
        # Nếu keyword bắt đầu bằng ký tự từ (a-z, 0-9), dùng \b phía trước.
        # Nếu keyword bắt đầu bằng symbol ($, #, @), dùng (?:^|\s) để bắt khoảng trắng.
        # Kiểm tra ký tự đầu tiên
        first_char = keyword[0] if keyword else ''
        last_char = keyword[-1] if keyword else ''
        
        prefix = r'\b' if first_char.isalnum() or first_char == '_' else r'(?:^|\s)'
        suffix = r'\b' if last_char.isalnum() or last_char == '_' else r'(?:\s|$)'
        
        return re.compile(f"{prefix}{escaped_kw}{suffix}", re.IGNORECASE)

    class Config:
        # Cho phép lưu private attributes (_compiled_...)
        underscore_attrs_are_private = True
        # Pydantic V2 compatibility (if needed, but Config is V1 style)
        extra = "ignore" 

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
        # UPDATE: Dùng \w để hỗ trợ tiếng Việt và các ngôn ngữ khác
        text = re.sub(r'[^\w\s$#@.-]', ' ', text)
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
        Kiểm tra khớp rule cực nhanh nhờ pre-compiled regex.
        """
        # 1. Check Must Not Have (Fail fast)
        for pattern in rule._compiled_must_not_have:
            if pattern.search(normalized_text):
                return False

        # 2. Check Must Have
        if not rule._compiled_must_have:
            return True # Pass nếu không có điều kiện

        # OR Logic: Chỉ cần 1 pattern khớp là được
        for pattern in rule._compiled_must_have:
            if pattern.search(normalized_text):
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
        # REMOVED: Global deduplication causes issues with channel-specific rules.
        # Example: User A wants msg from Channel X. Msg arrives from Channel Y first (cached).
        # Then arrives from Channel X (ignored due to cache). User A misses it.
        # We will handle deduplication per-user in the Worker Main loop.
        # if self.is_duplicate(normalized_text):
        #     return []

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
