"""
utils/helpers.py
Shared utility functions.
"""
import time
import hashlib
from functools import wraps
from typing import Callable, Any
from utils.logger import logger


def retry(max_attempts: int = 3, delay: float = 2.0, exceptions=(Exception,)):
    """Decorator to retry a function on failure."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    logger.warning(f"{func.__name__} attempt {attempt} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator


def generate_id(seed: str) -> str:
    """Generate a deterministic short ID from a string."""
    return hashlib.md5(seed.encode()).hexdigest()[:12]


def safe_int(value, default: int = 0) -> int:
    """Safely convert to int."""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert to float."""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def chunk_list(lst: list, size: int) -> list:
    """Split list into chunks of given size."""
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def normalize_name(name: str) -> str:
    """Normalize a researcher name for deduplication."""
    return " ".join(name.strip().lower().split())