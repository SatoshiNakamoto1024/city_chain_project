# D:\city_chain_project\network\DAGs\common\errors\test_errors.py
# D:\city_chain_project\network\DAGs\common\errors\test_errors.py
"""
pytest -q network/DAGs/common/errors/test_errors.py
"""
from __future__ import annotations

import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager          # ← Starlette 0.32+ ではこちらを使用

# パッケージ解決用（リポジトリ直下で pytest を叩く場合に備え）
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from errors.app_errors import app


# ───────────────────────────────────────────────
# 1) Retry 成功シナリオ（失敗 2 回まで）
# ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_retry_success() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as cli:
            r = await cli.get("/storage_flaky?key=t1&fails=2")
            assert r.status_code == 200
            assert r.json() == {"result": "ok"}


# ───────────────────────────────────────────────
# 2) Retry 上限超過 → 500 & StorageError
# ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_retry_exceeded() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as cli:
            r = await cli.get("/storage_flaky?key=t2&fails=10")
            assert r.status_code == 500
            assert r.json()["error"] == "StorageError"


# ───────────────────────────────────────────────
# 3) バリデーションエラー → 400 & ValidationError
# ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_validation_error() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as cli:
            r = await cli.get("/validate")  # クエリ q を省いてわざと失敗
            assert r.status_code == 400
            assert r.json()["error"] == "ValidationError"
