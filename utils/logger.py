"""
utils/logger.py
Centralized logging using loguru.
"""
import sys
import os
from loguru import logger as _logger
from config.settings import settings

os.makedirs("logs", exist_ok=True)

# Remove default handler
_logger.remove()

# Console handler
_logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log.LEVEL,
    colorize=True,
)

# File handler
_logger.add(
    settings.log.FILE,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=settings.log.LEVEL,
    rotation=settings.log.ROTATION,
    retention=settings.log.RETENTION,
    compression="zip",
)

logger = _logger