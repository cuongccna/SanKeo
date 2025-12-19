import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Telegram API
    API_ID: int = int(os.getenv("API_ID", "0"))
    API_HASH: str = os.getenv("API_HASH", "")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/sankeo_db")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Admin
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
    
    # Payment
    SEPAY_API_KEY: str = os.getenv("SEPAY_API_KEY", "")
    
    class Config:
        env_file = ".env"

settings = Settings()
