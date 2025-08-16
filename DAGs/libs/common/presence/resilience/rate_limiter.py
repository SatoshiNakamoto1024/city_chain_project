# D:\city_chain_project\network\DAGs\common\presence\resilience\rate_limiter.py
"""
presence.resilience.rate_limiter
--------------------------------
トークンバケット型 RateLimiter（async / thread-safe）
"""

from __future__ import annotations
import asyncio
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resilience.errors import RateLimitExceeded

class RateLimiter:
    """
    Parameters
    ----------
    rate : float
        毎秒補充するトークン数
    capacity : int
        最大バケットサイズ
    """

    def __init__(self, rate: float, capacity: int):
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._timestamp = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1):
        async with self._lock:
            now = time.time()
            elapsed = now - self._timestamp
            # トークン補充
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._timestamp = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return
            raise RateLimitExceeded("rate limit exceeded")
