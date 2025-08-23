# city_chain_project\network\DAGs\common\transport\retry_policy.py
"""
retry_policy.py
───────────────
汎用リトライ用デコレータ。

* backoff=`initial * (multiplier ** (attempt-1))`
* `exceptions` に渡した型 (タプル) のみ再試行対象とする
"""
from __future__ import annotations

import time
import functools
import logging
from typing import Callable, TypeVar, ParamSpec

import grpc                      # gRPC にも依存させずに済むよう import だけ

_T = TypeVar("_T")
_P = ParamSpec("_P")

logger = logging.getLogger(__name__)


def retry(
    *,
    max_attempts: int = 3,
    initial_backoff: float = 0.2,
    backoff_multiplier: float = 2.0,
    exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable[[_P, _T], _T]:
    """
    Parameters
    ----------
    max_attempts : int
        最大試行回数 (= 失敗を許容する回数 + 1)。既定 3。
    initial_backoff : float
        1 回目失敗後に待つ秒数。指数で増えていく。
    backoff_multiplier : float
        2 回目以降の backoff 乗数。
    exceptions :
        *再試行対象* とみなす例外型タプル。
        省略時は `(grpc.RpcError,)` のみ。
    """

    if exceptions is None:
        exceptions = (grpc.RpcError,)

    def decorator(fn: Callable[_P, _T]) -> Callable[_P, _T]:
        @functools.wraps(fn)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:  # type: ignore[override]
            backoff = initial_backoff
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as err:
                    if attempt == max_attempts:
                        logger.debug("retry: giving up after %s attempts", attempt)
                        raise
                    logger.debug(
                        "retry: caught %s (%s/%s) -> sleep %.3fs",
                        err.__class__.__name__,
                        attempt,
                        max_attempts,
                        backoff,
                    )
                    time.sleep(backoff)
                    backoff *= backoff_multiplier

        return wrapper

    return decorator
