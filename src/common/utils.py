import asyncio
import logging
from typing import Callable, Any
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)

async def safe_execution(coroutine: Callable[..., Any], *args, **kwargs) -> Any:
    """
    Wrapper to handle FloodWaitError automatically.
    If FloodWait is hit, it sleeps and retries.
    """
    while True:
        try:
            return await coroutine(*args, **kwargs)
        except FloodWaitError as e:
            logger.warning(f"Hit FloodWait! Sleeping for {e.seconds} seconds")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            logger.error(f"Error in safe_execution: {e}")
            raise e
