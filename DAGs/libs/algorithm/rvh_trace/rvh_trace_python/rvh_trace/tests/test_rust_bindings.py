# D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_python\tests\test_rust_bindings.py
# -*- coding: utf-8 -*-
"""
rvh_trace_python: Rust 拡張 (rvh_trace_rust) の健全性と
Python ラッパ API の挙動（sync/async/デコレータ）を本番想定で検証。

- Rust 拡張が無い環境では skip（maturin develop --release 済みを想定）
- init_tracing は冪等（複数回呼んでも OK）
- span は sync/async 両対応でログに名前が出る（caplog で検証）
- trace / trace_sync デコレータも同様に検証
"""

from __future__ import annotations

import importlib.util
import asyncio
import logging

import pytest

# ─────────────────────────────────────────────────────────────
# Rust 拡張が見つからなければ skip
# ─────────────────────────────────────────────────────────────
rs_spec = importlib.util.find_spec("rvh_trace_rust")
RUST_AVAILABLE = rs_spec is not None

pytestmark = pytest.mark.skipif(
    not RUST_AVAILABLE,
    reason="rvh_trace_rust が見つかりません。`maturin develop --release` を実行してからテストしてください。",
)

# 拡張がある時だけ import（mypy/ruff 向けに型: ignore を付与）
if RUST_AVAILABLE:  # pragma: no cover
    import rvh_trace_rust as rs  # type: ignore[import-not-found]
else:  # pragma: no cover
    rs = None  # type: ignore[assignment]

# Python ラッパ API
from rvh_trace import (  # noqa: E402  circular-safe
    init_tracing,
    span,
    trace,
    trace_sync,
)


# ─────────────────────────────────────────────────────────────
# セッション前に一度だけ Rust 側を初期化（冪等なので安心）
# ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def _setup_tracing() -> None:
    # 将来の挙動変化を避けるなら環境依存せず "debug" 程度で固定
    init_tracing("debug")


# ─────────────────────────────────────────────────────────────
# Rust 拡張の健全性
# ─────────────────────────────────────────────────────────────
def test_rust_extension_importable() -> None:
    assert hasattr(rs, "__doc__")
    # new_span が取れて record メソッドを持つこと（薄い健全性チェック）
    s = rs.new_span("health_check")
    assert hasattr(s, "record")
    s.record("k", "v")


def test_init_tracing_is_idempotent() -> None:
    # 2回目以降も例外を出さないこと
    init_tracing("info")
    init_tracing("warning")


# ─────────────────────────────────────────────────────────────
# span: sync / async 両対応のログ確認（Python 側は logger に名前を出す）
# ─────────────────────────────────────────────────────────────
def test_sync_span_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="rvh_trace")
    with span("sync_test", user=123, ok=True):
        pass
    assert "sync_test" in caplog.text


@pytest.mark.asyncio
async def test_async_span_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="rvh_trace")
    async with span("async_test", foo="bar"):
        await asyncio.sleep(0)
    assert "async_test" in caplog.text


def test_span_exception_safety(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="rvh_trace")
    try:
        with span("boom"):
            raise ValueError("boom")
    except ValueError:
        pass
    # 例外でも __exit__ が走り、ログは記録されている（落ちない）
    assert "boom" in caplog.text


def test_nested_spans(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="rvh_trace")
    with span("outer", a=1):
        with span("inner", b=2):
            pass
    text = caplog.text
    assert "outer" in text and "inner" in text


# ─────────────────────────────────────────────────────────────
# デコレータ: trace / trace_sync
# ─────────────────────────────────────────────────────────────
def test_trace_decorator_sync(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="rvh_trace")

    @trace("decor_sync", x=42)
    def f(a: int, b: int) -> int:
        return a + b

    assert f(1, 2) == 3
    assert "decor_sync" in caplog.text


@pytest.mark.asyncio
async def test_trace_decorator_async(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="rvh_trace")

    @trace("decor_async", y="ok")
    async def f(n: int) -> int:
        await asyncio.sleep(0)
        return n * 2

    assert await f(10) == 20
    assert "decor_async" in caplog.text


def test_trace_sync_alias(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="rvh_trace")

    @trace_sync("decor_sync_alias", z=True)
    def g() -> None:
        pass

    g()
    assert "decor_sync_alias" in caplog.text
