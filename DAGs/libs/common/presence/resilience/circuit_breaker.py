# D:\city_chain_project\network\DAGs\common\presence\resilience\circuit_breaker.py
"""
presence.resilience.circuit_breaker
-----------------------------------
失敗回数とクールダウン時間で OPEN / HALF-OPEN / CLOSED を管理する
非同期関数デコレータ実装
"""

from __future__ import annotations
import asyncio
import time
from enum import Enum, auto
from typing import Awaitable, Callable, Type
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resilience.errors import CircuitOpenError

class _State(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()

def circuit_breaker(
    *,
    max_failures: int = 5,
    reset_timeout: int = 30,
    error_types: tuple[Type[BaseException], ...] = (Exception,),
):
    """
    Usage::

        @circuit_breaker(max_failures=3, reset_timeout=15)
        async def my_call(): ...
    """
    def decorator(fn: Callable[..., Awaitable]):
        state = _State.CLOSED
        failures = 0
        opened_at = 0.0
        lock = asyncio.Lock()

        async def wrapper(*args, **kwargs):
            nonlocal state, failures, opened_at
            async with lock:
                # OPEN → HALF_OPEN
                if state == _State.OPEN and (time.time() - opened_at) >= reset_timeout:
                    state = _State.HALF_OPEN

                if state == _State.OPEN:
                    raise CircuitOpenError("circuit breaker is OPEN")

            try:
                result = await fn(*args, **kwargs)
            except error_types:
                async with lock:
                    failures += 1
                    if failures >= max_failures:
                        state = _State.OPEN
                        opened_at = time.time()
                raise
            else:
                async with lock:
                    failures = 0
                    state = _State.CLOSED
                return result

        return wrapper
    return decorator
