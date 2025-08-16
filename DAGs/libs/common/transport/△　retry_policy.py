# city_chain_project\network\DAGs\common\transport\retry_policy.py
"""
通信リトライ／指数バックオフ共通ロジック
"""
from __future__ import annotations
import time
import functools
import grpc
from typing import Callable, Sequence


def retry(
    max_attempts: int = 3,
    initial_backoff: float = 0.5,
    backoff_multiplier: float = 2.0,
    retryable_codes: Sequence[grpc.StatusCode] = (
        grpc.StatusCode.UNAVAILABLE,
        grpc.StatusCode.DEADLINE_EXCEEDED,
        grpc.StatusCode.RESOURCE_EXHAUSTED,
    ),
) -> Callable[[Callable], Callable]:
    """
    gRPC 呼び出しを再試行するデコレータ。

    Usage:
        @retry(max_attempts=5)
        def call_rpc(...):
            return stub.SomeMethod(...)
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            backoff = initial_backoff
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except grpc.RpcError as e:
                    code = e.code()
                    if attempt == max_attempts or code not in retryable_codes:
                        raise
                    time.sleep(backoff)
                    backoff *= backoff_multiplier
            # 最後にもう一度
            return fn(*args, **kwargs)
        return wrapper
    return decorator
