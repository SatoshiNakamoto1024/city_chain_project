# D:\city_chain_project\network\DAGs\common\presence\resilience\rate_limiter.py
import time
from .errors import RateLimitExceeded

class TokenBucket:
    """
    トークンバケット方式レートリミッター。
    rate：1秒あたりのトークン補充レート
    capacity：バケットの最大トークン数
    """
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last = time.time()

    def _refill(self):
        now = time.time()
        elapsed = now - self._last
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last = now

    def acquire(self, tokens: int = 1):
        """
        トークンを消費できれば即時戻る。足りなければ RateLimitExceeded を投げる。
        """
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
        else:
            raise RateLimitExceeded(f"Rate limit exceeded: need {tokens}, have {self._tokens:.2f}")
