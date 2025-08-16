# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\tests\test_sender.py
import asyncio

import pytest

from poh_request.utils import (
    async_backoff_retry,
    b58decode,
    b58encode,
    generate_nonce,
)


def test_b58_roundtrip():
    data = b"hello"
    assert b58decode(b58encode(data)) == data


def test_nonce_unique():
    assert generate_nonce() != generate_nonce()


@pytest.mark.asyncio
async def test_backoff_success(monkeypatch):
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError
        return "ok"

    assert await async_backoff_retry(fn, attempts=5, base_delay=0.01) == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_backoff_exhaust():
    async def bad():
        raise RuntimeError

    with pytest.raises(RuntimeError):
        await async_backoff_retry(bad, attempts=2, base_delay=0.001)
