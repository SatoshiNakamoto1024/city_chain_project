# D:\city_chain_project\network\DAGs\common\grpc_dag\client\retry.py
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
):
    """
    指定された gRPC 呼び出しをリトライするデコレータ。
    指数バックオフを用い、retryable_codes の場合にのみ再試行。
    """
    def decorator(fn: Callable):
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
            # 最後まで返らなかったら例外
            return fn(*args, **kwargs)
        return wrapper
    return decorator
