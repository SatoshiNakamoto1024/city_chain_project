# D:\city_chain_project\DAGs\libs\algorithm\poh_request\poh_request\sender.py
# poh_request/sender.py
from __future__ import annotations
import asyncio
from typing import Any

import httpx

from .config import settings
from .exceptions import SendError
from .schema import PoHResponse
from .utils import async_backoff_retry


class AsyncSender:
    def __init__(
        self,
        *,
        timeout: float | None = None,
        attempts: int = 1,          # ★ デフォルト1回に
    ) -> None:
        self._timeout = timeout or settings.request_timeout
        self._attempts = attempts

    async def send(self, payload_b58: str) -> PoHResponse:
        async def _once() -> PoHResponse:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post(settings.rpc_endpoint, content=payload_b58)
                if res.status_code >= 400:
                    raise SendError(f"HTTP {res.status_code}: {res.text}")
                return PoHResponse.model_validate_json(res.text)

        return await async_backoff_retry(_once, attempts=self._attempts)


# ------------------------------------------------------------------ #
# convenience helpers
# ------------------------------------------------------------------ #
async def send(payload_b58: str) -> PoHResponse:
    return await AsyncSender().send(payload_b58)


def send_sync(payload_b58: str) -> PoHResponse:  # noqa: D401
    """
    同期環境から呼ぶためのラッパ。  
    モンキーパッチで ``AsyncSender.send`` が同期関数に
    置き換えられた場合にも対応する。
    """
    maybe_coro: Any = AsyncSender().send(payload_b58)
    if asyncio.iscoroutine(maybe_coro):
        return asyncio.run(maybe_coro)
    return maybe_coro  # already a PoHResponse
