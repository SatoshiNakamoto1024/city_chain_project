# File: login/user_manager/utils/test_utils.py
# -*- coding: utf-8 -*-
"""
pytest でサーバーを起動し、『登録 → ストレージ OK → 100 MB 予約通知 →
device_auth ログイン』の 3 連フローを確認する。

この 3 ステップは Android 側の
  - AuthApiServiceIntegrationTest.kt
  - StorageApiServiceIntegrationTest.kt
  - FileManagerTest.kt
と同等の意味合いになる。
"""
import os, sys, time, json, subprocess, uuid, base64
from pathlib import Path
import requests
import pytest

ROOT = Path(__file__).resolve().parents[2]          # <project root>/login
SERVER_SCRIPT = ROOT / "android" / "app_flask.py"   # 8888 ポートで起動
BASE = "http://127.0.0.1:8888"

# ---------------------------------------------------------------------------
# テスト用共通変数をモジュールスコープで持つ
# ---------------------------------------------------------------------------
_user = {}          # register の戻り値を丸ごと詰め込む
_password = "TestPass123!"


# ---------------------------------------------------------------------------
# ❶ サーバーをサブプロセスで起動するフィクスチャ（module 単位）
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def run_server():
    proc = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2.5)       # 起動待ち
    yield
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# ❷ ここからテストケース
# ---------------------------------------------------------------------------
class TestEndToEnd:

    # ---------- 1) register -------------------------------------------------
    def test_01_register(self):
        uname = f"py_{uuid.uuid4().hex[:8]}"
        payload = {
            "username": uname,
            "email":    f"{uname}@example.com",
            "password": _password
        }
        r = requests.post(f"{BASE}/register/", json=payload, timeout=10)
        assert r.status_code == 200, r.text

        body = r.json()
        assert body.get("success") is True
        assert "uuid" in body

        # 保持して 2,3 ケースで使う
        global _user
        _user = body

    # ---------- 2) /utils/check_storage ------------------------------------
    def test_02_storage_probe(self):
        # User-Agent から android と判定させる
        hdrs = {"User-Agent":
                "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro Build/UPB) "}
        r = requests.get(f"{BASE}/utils/check_storage", headers=hdrs, timeout=5)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["storage_ok"] is True
        assert body["platform_type"] == "android"

    # ---------- 3) /user/storage_check -------------------------------------
    def test_03_storage_reservation(self):
        req = {
            "userUuid":      _user["uuid"],
            "reservedBytes": 100 * 1024 * 1024            # 100 MB
        }
        r = requests.post(f"{BASE}/user/storage_check", json=req, timeout=5)
        assert r.status_code == 200, r.text
        assert r.json().get("success") is True

    # ---------- 4) /device_auth/login  (≒ Android の Storage+Auth) ---------
    def test_04_device_auth_login(self):
        hdrs = {"User-Agent":
                "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/UPB)",
                "X-Device-Type": "android"}
        req = {
            "username":          _user["username"],
            "password":          _password,
            "client_free_space": 150 * 1024 * 1024        # 150 MB
        }
        r = requests.post(f"{BASE}/device_auth/login", headers=hdrs,
                          json=req, timeout=10)

        # auth_py.login() がユーザー認証を行う。
        # ここでは「登録直後のユーザーなので成功」を期待する。
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True
        assert body.get("jwt_token")          # JWT が返る
        assert body.get("uuid") == _user["uuid"]
