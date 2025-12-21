from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Numeric, Integer, Time, Text, JSON
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
