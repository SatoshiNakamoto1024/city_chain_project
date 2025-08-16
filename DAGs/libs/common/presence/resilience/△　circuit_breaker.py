# D:\city_chain_project\network\DAGs\common\presence\resilience\circuit_breaker.py
import time
from .errors import CircuitOpenError

class CircuitBreaker:
    """
    簡易サーキットブレーカー (async非対応メソッドでも動きます)：
      - fail_max 回連続で失敗すると OPEN → 一定時間後 HALF_OPEN → 成功で CLOSED に戻る
    """
    def __init__(self, fail_max: int = 5, reset_timeout: float = 60.0):
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._failure_count = 0
        self._state = "CLOSED"       # CLOSED, OPEN, HALF_OPEN
        self._opened_at = 0.0

    def _current_time(self) -> float:
        return time.time()

    def _enter_open(self):
        self._state = "OPEN"
        self._opened_at = self._current_time()

    def _attempt_reset(self):
        if self._state == "OPEN" and (self._current_time() - self._opened_at) >= self.reset_timeout:
            self._state = "HALF_OPEN"

    def call(self, func, *args, **kwargs):
        """
        同期 or 非同期な func を包んで呼び出す。
        OPEN 状態では CircuitOpenError を即時投げ。
        """
        self._attempt_reset()
        if self._state == "OPEN":
            raise CircuitOpenError("Circuit is open; skipping call")

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            self._failure_count += 1
            if self._failure_count >= self.fail_max:
                self._enter_open()
            raise
        else:
            # 成功したらリセット
            self._failure_count = 0
            self._state = "CLOSED"
            return result
