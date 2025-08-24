# \city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_python\tests\test_trace.py

import asyncio
import pytest

from rvh_trace import init_tracing, span, trace


@pytest.fixture(scope="session", autouse=True)
def _setup_tracing() -> None:
    init_tracing("debug")


@pytest.mark.asyncio
async def test_async_span_records(caplog):
    caplog.set_level("DEBUG")
    async with span("async_test", foo="bar"):
        assert "async_test" in caplog.text


def test_sync_trace_decorator(caplog):
    caplog.set_level("INFO")

    @trace("sync_op", x=42)
    def f():
        pass

    f()
    assert "sync_op" in caplog.text


@pytest.mark.asyncio
async def test_trace_decorator_async(caplog):
    caplog.set_level("INFO")

    @trace("async_op", y=99)
    async def f():
        await asyncio.sleep(0)

    await f()
    assert "async_op" in caplog.text
