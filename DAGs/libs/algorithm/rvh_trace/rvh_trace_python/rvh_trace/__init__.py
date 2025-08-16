# D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_python\rvh_trace\__init__.py
"""
rvh_trace
=========

*Rust 実装* `rvh_trace_rust` を薄く包み、Pythonic な

- `init_tracing(level)`
- `span(name, **fields)`   … sync/async 両対応のコンテキストマネージャ
- `trace(name, **fields)`  … sync/async 両対応の関数デコレータ
"""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Any, Optional, Type

# Rust 拡張ロード ────────────────────────────────────────────────
from rvh_trace_rust import (
    init_tracing as _init_tracing_rust,
    new_span as _new_span,
)

# Python 標準 logger を用意（テストはここを caplog で捕まえる）
_logger = logging.getLogger("rvh_trace")


# ────────────────────────────────────────────────────────────────
# public API: init_tracing
# ────────────────────────────────────────────────────────────────
def init_tracing(level: str = "info") -> None:
    """Rust 側で tracing-subscriber を初期化（idempotent）"""
    _init_tracing_rust(level)


# ────────────────────────────────────────────────────────────────
# Span コンテキストマネージャ（sync / async 両対応）
# ────────────────────────────────────────────────────────────────
class _SpanCM:
    """with / async with どちらでも使えるコンテキスト"""

    def __init__(self, name: str, **fields: Any) -> None:
        self._name = name
        self._span = _new_span(name)
        for k, v in fields.items():
            self._span.record(k, str(v))

    # ---------- 同期 ----------
    def __enter__(self) -> "_SpanCM":  # type: ignore[override]
        _logger.info(self._name)      # ← ここがテストで caplog に捕まる
        return self

    def __exit__(                    # type: ignore[override]
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        del self._span  # drop で Rust 側 Span を閉じる

    # ---------- 非同期 ----------
    async def __aenter__(self) -> "_SpanCM":
        _logger.info(self._name)      # async 版も同じく
        return self

    async def __aexit__(             # noqa: D401
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        del self._span


def span(name: str, **fields: Any) -> _SpanCM:
    """sync/async どちらでも使える span"""
    return _SpanCM(name, **fields)


# ────────────────────────────────────────────────────────────────
# デコレータ（trace / trace_sync）
# ────────────────────────────────────────────────────────────────
from .trace_builder import trace, trace_sync  # noqa: E402  circular-safe

__all__ = [
    "init_tracing",
    "span",
    "trace",
    "trace_sync",
]

# バージョン文字列
from ._version import __version__  # noqa: E402
