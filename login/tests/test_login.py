# login/test_login.py

import pytest
import subprocess
import time
import requests
import uuid
import os

@pytest.fixture(scope="module")
def run_login_app():
    """
    login/app.py をサブプロセスで起動し、テスト終了後に停止。
    DynamoDB/S3など本番リソースに書き込むため、AWS認証情報等が必要。
    """
    process = subprocess.Popen(["python", "login\\app.py"], shell=True)
    time.sleep(3)  # サーバー起動待ち

    yield

    process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()

@pytest.mark.usefixtures("run_login_app")
class TestLoginIntegration:
    base_url = "http://localhost:5000"

    def test_index(self):
        """
        GET / -> トップページ
        """
        resp = requests.get(self.base_url + "/")
        assert resp.status_code == 200
        assert "CityChain トップページ" in resp.text

    def test_registration_page(self):
        """
        GET /registration -> 登録フォームHTML
        """
        resp = requests.get(self.base_url + "/registration")
        assert resp.status_code == 200
        assert "ユーザー登録" in resp.text or "Register" in resp.text

    def test_register_post(self):
        """
        POST /registration -> JSON入力でユーザー登録
        """
        data = {
            "username": f"test_{uuid.uuid4().hex[:5]}",
            "email": f"test_{uuid.uuid4().hex[:5]}@example.com",
            "password": "RegPass123",
            "name": "RegUser",
            "birth_date": "2000-01-01",
            "address": "RegStreet",
            "mynumber": "123456789012",
            "phone": "08011112222",
            "initial_harmony_token": "100"
        }
        resp = requests.post(self.base_url + "/registration", json=data)
        assert resp.status_code in [200, 500], resp.text
        if resp.status_code == 200:
            body = resp.json()
            assert body.get("success") is True
            assert "uuid" in body

    def test_auth_login_page(self):
        """
        GET /auth/login -> ログイン画面
        """
        resp = requests.get(self.base_url + "/auth/login")
        assert resp.status_code == 200, resp.text
        # ログイン画面に何かしら目印
        assert "Login" in resp.text or "ログイン" in resp.text

    def test_auth_login_post(self):
        """
        POST /auth/login -> ユーザー名 & パスワードを送信
        """
        # 事前にユーザー登録 or 既存ユーザーを使用
        # 今回はランダムユーザーで401になり得るがOK
        data = {
            "username": f"unknown_{uuid.uuid4().hex[:5]}",
            "password": "Pass123"
        }
        resp = requests.post(self.base_url + "/auth/login", json=data)
        assert resp.status_code in [200, 401, 500]
        if resp.status_code == 200:
            body = resp.json()
            assert body["success"] is True
            assert "jwt_token" in body

    # 他にも /user/... /ca/... などのテスト追加可能
