# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\utils.py
"""Utility helpers (Base58, nonce, async‑retry)."""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Awaitable, Callable, TypeVar
from .exceptions import SendError
import base58

T = TypeVar("T")


def b58encode(data: bytes) -> str:
    return base58.b58encode(data).decode()


def b58decode(s: str) -> bytes:
    return base58.b58decode(s.encode())


# -------- nonce --------------------------------------------------------- #
def generate_nonce() -> int:
    """Return a 64‑bit random nonce."""
    return random.getrandbits(64)


# -------- generic async back‑off retry ---------------------------------- #
async def async_backoff_retry(
    coro_factory: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.2,
) -> T:
    """
    Retry helper with exponential backoff.
    """
    for attempt in range(1, attempts + 1):
        try:
            return await coro_factory()
        except SendError:      # ★ ← SendError は即座に伝播
            raise
        except Exception:      # pragma: no cover
            if attempt == attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1)) * (0.8 + random.random() * 0.4)
            await asyncio.sleep(delay)