import asyncio
from functools import wraps


def retry(
    max_attempts: int = 5,
    initial_delay: float = 0.1,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    非同期関数向けデコレータ：
    送信失敗時に指数バックオフで再試行（最大 max_attempts 回）
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions:
                    if attempt == max_attempts:
                        raise
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator
