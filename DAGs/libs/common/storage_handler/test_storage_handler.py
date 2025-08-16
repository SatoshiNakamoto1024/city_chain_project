# city_chain_project\network\DAGs\common\storage_handler\test_storage_handler.py
"""
E2E テスト: StorageHandler HTTP API

- 環境変数で一時ディレクトリを設定
- MIN_FREE を 0 にしてテストしやすく
- GET /has_space, POST /save を網羅
- 未サポート device_type と無効 base64 も検証
"""
from __future__ import annotations
import base64
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage_handler.app_storage_handler import app

# 定数を上書き
BASE_MOD = "network.DAGs.common.storage_handler.base"


@pytest.fixture(autouse=True)
def setup_env(tmp_path, monkeypatch):
    # 各ハンドラの ROOT_DIR を tmp_path 以下に向ける
    monkeypatch.setenv("ANDROID_STORAGE_DIR", str(tmp_path / "android"))
    monkeypatch.setenv("IOS_STORAGE_DIR", str(tmp_path / "ios"))
    monkeypatch.setenv("IOT_STORAGE_DIR", str(tmp_path / "iot"))
    monkeypatch.setenv("GAME_STORAGE_DIR", str(tmp_path / "game"))
    # テストでは空き要件をゼロにして失敗しないように
    monkeypatch.setattr(f"{BASE_MOD}.MIN_FREE", 0)
    yield


@pytest.mark.asyncio
async def test_storage_handler_endpoints(tmp_path):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as cli:
        # 1) has_space 成功パス (android, size=1)
        r = await cli.get("/has_space", params={"device_type": "android", "size": 1})
        assert r.status_code == 200
        body = r.json()
        assert body["device_type"] == "android"
        assert body["size"] == 1
        assert body["has_space"] is True

        # 2) save_fragment 成功パス
        raw = b"hello"
        data_b64 = base64.b64encode(raw).decode()
        r = await cli.post("/save", json={
            "device_type": "android",
            "name": "frag1",
            "data": data_b64,
        })
        assert r.status_code == 200
        assert r.json()["saved"] is True

        # ファイルが正しく書かれたか
        saved_path = tmp_path / "android" / "frag1"
        assert saved_path.exists()
        assert saved_path.read_bytes() == raw

        # 3) unsupported device_type
        r = await cli.get("/has_space", params={"device_type": "unknown", "size": 0})
        assert r.status_code == 400

        r = await cli.post("/save", json={
            "device_type": "unknown",
            "name": "x",
            "data": data_b64,
        })
        assert r.status_code == 400

        # 4) invalid base64
        r = await cli.post("/save", json={
            "device_type": "android",
            "name": "x",
            "data": "!!!!!notbase64",
        })
        assert r.status_code == 400

        # 5) 他ハンドラ (ios, iot, game) も同様に has_space が True
        for dev in ("ios", "iot", "game"):
            r = await cli.get("/has_space", params={"device_type": dev, "size": 2})
            assert r.status_code == 200
            assert r.json()["has_space"] is True
