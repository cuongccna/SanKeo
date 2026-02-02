from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Numeric, Integer, Time, Text, JSON, Float, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class AnalysisTemplate(Base):
    __tablename__ = "analysis_templates"

    code = Column(String, primary_key=True) # e.g., 'WHALE_FLOW'
    name = Column(String, nullable=False)
    required_tags = Column(JSON, nullable=False) # List of tags e.g. ['ONCHAIN', 'PRICE_ACTION']
    time_window_minutes = Column(Integer, default=60)
    prompt_template = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserTemplateSubscription(Base):
    __tablename__ = "user_template_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    template_code = Column(String, ForeignKey("analysis_templates.code"), nullable=False)
    last_sent_at = Column(DateTime(timezone=True), nullable=True) # Thời điểm gửi báo cáo gần nhất
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PlanType(str, enum.Enum):
    FREE = "FREE"
    VIP = "VIP"
    BUSINESS = "BUSINESS"

class SourceTag(str, enum.Enum):
    NEWS_VIP = "NEWS_VIP"
    SIGNAL = "SIGNAL"
    ONCHAIN = "ONCHAIN"
    NORMAL = "NORMAL"

class SourceConfig(Base):
    __tablename__ = "source_configs"

    chat_id = Column(BigInteger, primary_key=True, index=True) # Channel/Group ID
    name = Column(String, nullable=True)
    tags = Column(JSON, default=[]) # List of tags e.g. ['NEWS_VIP', 'SIGNAL']
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)  # Telegram User ID
    username = Column(String, nullable=True)
    plan_type = Column(String, default=PlanType.FREE) # Stored as string for simplicity
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Affiliate
    referrer_id = Column(BigInteger, nullable=True)
    commission_balance = Column(Numeric, default=0.0)
    
    # Quiet Mode
    quiet_start = Column(Time, nullable=True)
    quiet_end = Column(Time, nullable=True)

    rules = relationship("FilterRule", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user")
    forwarding_targets = relationship("UserForwardingTarget", back_populates="user", cascade="all, delete-orphan")

class UserForwardingTarget(Base):
    __tablename__ = "user_forwarding_targets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="forwarding_targets")

class FilterRule(Base):
    __tablename__ = "filter_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    keyword = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="rules")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True) # Bank Transaction ID
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric, nullable=False)
    status = Column(String, default="SUCCESS")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")

class BlacklistedChannel(Base):
    __tablename__ = "blacklisted_channels"

    channel_id = Column(BigInteger, primary_key=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============ NEWS STORAGE WITH DEDUP & COMPRESSION ============

class CryptoNews(Base):
    """
    Main news table with dedup via content_hash.
    Stores compressed text to reduce DB size.
    """
    __tablename__ = "crypto_news"
    __table_args__ = (
        Index('idx_content_hash', 'content_hash'),
        Index('idx_source_id', 'source_id'),
        Index('idx_created_at', 'created_at'),
        Index('idx_final_weight', 'final_weight'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Deduplication: content_hash = SHA256(normalized_text)
    content_hash = Column(String(64), unique=True, index=True, nullable=False)
    
    # Source info
    source_id = Column(BigInteger, nullable=False)  # Telegram chat_id
    source_name = Column(String, nullable=False)
    message_id = Column(Integer, nullable=True)
    
    # Content (compressed in storage)
    text_summary = Column(String(500), nullable=False)  # First 500 chars
    text_full = Column(Text, nullable=True)  # Full text if important (weight >= 70)
    
    # Filter results
    layer1_matched_keywords = Column(JSON, nullable=True)  # {"ticker": ["BTC"], ...}
    layer2_quality_score = Column(Float, nullable=True)  # 0-100
    layer2_sentiment = Column(String, nullable=True)  # bullish|neutral|bearish
    layer2_urgency = Column(String, nullable=True)  # breaking|important|regular
    layer2_credibility = Column(Float, nullable=True)  # 0-100
    
    layer3_relevance = Column(Float, nullable=True)  # 0-100
    layer3_credibility = Column(Float, nullable=True)  # 0-100
    layer3_market_impact = Column(Float, nullable=True)  # 0-100
    final_weight = Column(Float, nullable=True)  # Final score 0-100
    ai_reasoning = Column(Text, nullable=True)
    
    # Metadata
    message_link = Column(String, nullable=True)
    image_path = Column(String, nullable=True)
    tags = Column(JSON, default=[])  # ["ONCHAIN", "SIGNAL", ...]
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    occurrences = Column(Integer, default=1)  # How many times seen (dedup counter)
    
    # Engagement (optional, for future analytics)
    view_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    user_feedback = Column(Integer, default=0)  # +1: useful, -1: spam, 0: neutral


class NewsDuplicate(Base):
    """
    Track duplicate messages by content_hash.
    Keeps references to all duplicate instances.
    Used to prevent showing same news multiple times.
    """
    __tablename__ = "news_duplicates"
    __table_args__ = (
        Index('idx_content_hash', 'content_hash'),
        Index('idx_first_news_id', 'first_news_id'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Hash of content
    content_hash = Column(String(64), nullable=False, index=True)
    
    # Reference to "canonical" news record
    first_news_id = Column(BigInteger, ForeignKey("crypto_news.id"), nullable=False)
    
    # Duplicate instance info
    source_id = Column(BigInteger, nullable=False)
    message_id = Column(Integer, nullable=True)
    
    # Similarity metrics
    cosine_similarity = Column(Float, default=0.95)  # How similar to canonical (0-1)
    text_diff_ratio = Column(Float, nullable=True)  # Diff ratio
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NewsArchive(Base):
    """
    Archive old news (> 7 days) in compressed format.
    Move data here to reduce main table size.
    
    Strategy: Keep hot data in crypto_news (7 days),
    move to archive after.
    """
    __tablename__ = "news_archive"
    __table_args__ = (
        Index('idx_archived_at', 'archived_at'),
    )
    
    id = Column(BigInteger, primary_key=True)  # Same as crypto_news.id
    content_hash = Column(String(64), unique=True)
    
    # Compressed summary
    summary = Column(String(200), nullable=False)
    
    # Aggregated stats
    total_occurrences = Column(Integer, default=1)
    final_weight = Column(Float, nullable=True)
    sentiment = Column(String, nullable=True)
    
    archived_at = Column(DateTime(timezone=True), server_default=func.now())
    original_created_at = Column(DateTime(timezone=True), nullable=False)
