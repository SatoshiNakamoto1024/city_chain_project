# D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_integration.py
# !/usr/bin/env python3
"""
End-to-End integration test for rvh_trace
========================================
pytest -v rvh_trace_integration.py
"""

from __future__ import annotations

import asyncio
import logging
import pathlib
import sys
from types import ModuleType

import pytest
pytestmark = pytest.mark.ffi

# ---------------------------------------------------------------------------
# import path set-up so that local builds are picked first
# ---------------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parent
PY_PKG = ROOT / "rvh_trace_python"
WHEEL_DIR = ROOT / "rvh_trace_rust" / "target" / "wheels"

if PY_PKG.exists():
    sys.path.insert(0, str(PY_PKG))
if WHEEL_DIR.is_dir():
    sys.path.insert(0, str(WHEEL_DIR))

import rvh_trace                      # noqa: E402
import rvh_trace_rust as _rust_mod    # noqa: E402

assert isinstance(_rust_mod, ModuleType)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _setup_tracing() -> None:
    rvh_trace.init_tracing("debug")


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_span_integration(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    async with rvh_trace.span("e2e_async", answer=42):
        await asyncio.sleep(0)
    assert "e2e_async" in caplog.text


def test_sync_span_integration(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    with rvh_trace.span("e2e_sync", foo="bar"):
        pass
    assert "e2e_sync" in caplog.text


def test_trace_decorator_sync(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    @rvh_trace.trace("decor_sync", x=1)
    def work() -> None:
        return

    work()
    assert "decor_sync" in caplog.text


@pytest.mark.asyncio
async def test_trace_decorator_async(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    @rvh_trace.trace("decor_async", y=2)
    async def work() -> None:
        await asyncio.sleep(0)

    await work()
    assert "decor_async" in caplog.text


def test_direct_rust_span(caplog: pytest.LogCaptureFixture) -> None:
    """Rust の `new_span()` が Python から呼べて例外が出ないことを確認"""
    span = _rust_mod.new_span("rust_native")
    span.record("k", "v")
    del span  # drop OK
    assert True   # 例外さえ出なければ合格


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
