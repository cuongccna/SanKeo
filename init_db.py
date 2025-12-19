"""
Script để khởi tạo database tables.
Chạy: python init_db.py
"""
import asyncio
from src.database.db import init_db
from src.common.logger import get_logger

logger = get_logger("init_db")

async def main():
    logger.info("Initializing database tables...")
    await init_db()
    logger.info("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(main())
