import sys
from loguru import logger

# Configure logger
logger.remove() # Remove default handler
logger.add(sys.stderr, level="INFO")
logger.add("logs/app.log", rotation="10 MB", level="DEBUG", compression="zip")

def get_logger(name: str):
    return logger.bind(name=name)
