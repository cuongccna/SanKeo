import os
import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
from src.common.logger import get_logger
from src.common.redis_client import get_redis

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
logger = get_logger("bot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Welcome to Personal Alpha Hunter! Use /add to add keywords.")

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    # Logic to add keyword to DB
    await message.answer("Keyword added (Placeholder).")

@dp.message(Command("pay"))
async def cmd_pay(message: types.Message):
    # Logic to show payment info
    await message.answer("Please transfer to account XYZ...")

async def notification_worker():
    redis = await get_redis()
    logger.info("Starting Notification Worker...")
    while True:
        try:
            _, data = await redis.brpop("queue:notifications")
            notification = json.loads(data)
            user_id = notification["user_id"]
            msg_data = notification["message"]
            keyword = notification["matched_keyword"]
            
            text = f"🔔 Match: {keyword}\n\n{msg_data['text']}"
            await bot.send_message(user_id, text)
            
        except Exception as e:
            logger.error(f"Notification error: {e}")
            await asyncio.sleep(1)

async def main():
    logger.info("Starting Bot Interface...")
    asyncio.create_task(notification_worker())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
