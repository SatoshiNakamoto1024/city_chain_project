# File: login/user_manager/utils/test_utils.py

import pytest
import requests
import subprocess
import time, os

"""
このファイルは、Pytest でサーバー(login_handler.py)を一時起動し、
/device_auth/login エンドポイントを叩いてレスポンスを検証します。

ここでは:
 - PC想定: User-AgentがPC系 → サーバー側ディスクチェック → 結果が200 (認証OK), 403 (ストレージ不足), 401 (認証NG)
 - Android想定: client_free_spaceを送ってOK(>=100MB)ならストレージOK → 認証OK(200) or 認証NG(401)
"""
@pytest.fixture(scope="module")
def run_server():
    """
    login_handler.py をサブプロセスで起動し、テスト完了後に終了させる。
    """
    # login_handler.py の先頭で Blueprint を登録し、app.run() していることが前提です
    process = subprocess.Popen(
        ["python", "login_handler.py"],
        shell=True, cwd=os.path.dirname(__file__)
    )
    time.sleep(2)  # サーバー起動待ち
    yield
    process.terminate()
    try:
        process.wait(timeout=3)
    except:
        process.kill()

@pytest.mark.usefixtures("run_server")
class TestLoginHandler:
    base_url = "http://127.0.0.1:5050"

    def test_login_pc_storage_and_auth(self):
        """
        PC想定。
        - User-Agent: Windows → サーバー側ディスクチェック
        - storage OK なら認証を呼び出す → 実ユーザー不在なら401
        - storage NG なら403
        """
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        payload = {"username": "admin", "password": "password"}
        resp = requests.post(f"{self.base_url}/device_auth/login",
                             headers=headers, json=payload)

        # 200 (認証OK), 401 (認証NG), 403 (ストレージNG) のいずれか
        assert resp.status_code in (200, 401, 403)

        body = resp.json()
        # レスポンスに `success` フィールドが必ず含まれること
        assert "success" in body
        if resp.status_code == 200:
            assert body["success"] is True
        else:
            assert body["success"] is False

    def test_login_android_storage_and_auth(self):
        """
        Android想定。
        - User-Agent: Android → client_free_space を使ってストレージ判定
        - client_free_space=200MB なら storage OK → 認証 200 or 401
        """
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G975F)"}
        payload = {
            "username": "admin",
            "password": "password",
            "client_free_space": 200 * 1024 * 1024
        }
        resp = requests.post(f"{self.base_url}/device_auth/login",
                             headers=headers, json=payload)

        # 200 (認証OK), 401 (認証NG) のいずれか
        assert resp.status_code in (200, 401)

        body = resp.json()
        assert "success" in body
        if resp.status_code == 200:
            assert body["success"] is True
        else:
            assert body["success"] is False
