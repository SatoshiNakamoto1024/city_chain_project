# D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_python\rvh_trace\trace_builder.py
"""
trace_builder
=============

`@trace(...)` デコレータで関数呼び出し全体を span で囲むユーティリティ。
同期 / 非同期どちらの関数にも使えます。
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, TypeVar

from . import span  # 循環回避：import 時に span は既に定義済み

T = TypeVar("T", bound=Callable[..., Any])


def _wrap_async(fn: Callable[..., Any], name: str, fields: dict[str, Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        async with span(name, **fields):
            return await fn(*args, **kwargs)

    return wrapper


def _wrap_sync(fn: Callable[..., Any], name: str, fields: dict[str, Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with span(name, **fields):
            return fn(*args, **kwargs)

    return wrapper


def trace(name: str | None = None, **fixed_fields: Any) -> Callable[[T], T]:
    """
    汎用デコレータ。

    ```python
    @trace("op", user=123)
    async def work():
        ...

    @trace()  # name 省略時は関数名
    def pure():
        ...
    ```
    """
    def decorator(fn: T) -> T:  # type: ignore[valid-type]
        _name = name or fn.__name__
        if inspect.iscoroutinefunction(fn):
            return _wrap_async(fn, _name, fixed_fields)  # type: ignore[return-value]
        return _wrap_sync(fn, _name, fixed_fields)       # type: ignore[return-value]

    return decorator


# 同期専用 syntactic sugar
def trace_sync(name: str | None = None, **fields: Any) -> Callable[[T], T]:
    def decorator(fn: T) -> T:  # type: ignore[valid-type]
        return _wrap_sync(fn, name or fn.__name__, fields)  # type: ignore[return-value]

    return decorator


__all__ = ["trace", "trace_sync"]
