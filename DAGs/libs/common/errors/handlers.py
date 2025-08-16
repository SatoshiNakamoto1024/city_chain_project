# D:\city_chain_project\network\DAGs\common\errors\handlers.py
"""
handlers.py  ― 例外ハンドリングの統一窓口
"""
from __future__ import annotations
import asyncio
import functools
import time
from typing import Callable, ParamSpec, TypeVar, Awaitable, Any
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from errors.exceptions import BaseError
from errors.policies import get_policy
from errors.logger import log_exception

P = ParamSpec("P")
R = TypeVar("R")


def _sleep(sec: float) -> None | Awaitable[None]:
    """sync / async どちらでも使える sleep ラッパー"""
    if asyncio.iscoroutinefunction(lambda: None):
        return asyncio.sleep(sec)
    time.sleep(sec)
    return None


def handle(fn: Callable[P, R]) -> Callable[P, R]:
    """
    デコレーター:
        @errors.handle
        def my_func(...):
            ...
    """

    if asyncio.iscoroutinefunction(fn):  # ───── async 関数
        @functools.wraps(fn)
        async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore[override]
            attempt = 0
            while True:
                try:
                    return await fn(*args, **kwargs)
                except BaseError as exc:
                    policy = get_policy(exc)
                    log_exception(exc)
                    if attempt >= policy.max_attempts:
                        raise
                    attempt += 1
                    await asyncio.sleep(policy.initial_backoff * attempt)

        return _wrapper  # type: ignore[return-value]

    # ───────── sync 関数
    @functools.wraps(fn)
    def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore[override]
        attempt = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except BaseError as exc:
                policy = get_policy(exc)
                log_exception(exc)
                if attempt >= policy.max_attempts:
                    raise
                attempt += 1
                time.sleep(policy.initial_backoff * attempt)

    return _wrapper  # type: ignore[return-value]
