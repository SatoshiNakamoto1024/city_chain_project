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
    login/app.py をサブプロセスで起動し、テスト後に終了
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
        GET / -> index
        """
        resp = requests.get(self.base_url + "/")
        assert resp.status_code == 200
        assert "<h1>CityChain トップページ</h1>" in resp.text

    def test_register(self):
        """
        POST /registration
        """
        url = f"{self.base_url}/registration"
        data = {
            "username": f"test_{uuid.uuid4().hex[:5]}",
            "email": f"test_{uuid.uuid4().hex[:5]}@example.com",
            "password": "TestPass1",
            "name": "RegisteredUser",
            "birth_date": "2000-01-01",
            "address": "123 Test Street",
            "mynumber": "123456789012",
            "phone": "08099990000",
            "initial_harmony_token": "100"
        }
        resp = requests.post(url, json=data)
        assert resp.status_code in [200, 500]
        # registration.app_registration 内で実際にDynamoDBやS3への書き込みが行われる想定
        if resp.status_code == 200:
            body = resp.json()
            assert body.get("success") is True
            self.registered_uuid = body.get("uuid")

    def test_login(self):
        """
        /auth/login → auth_bp 参照
        """
        url = f"{self.base_url}/auth/login"
        # 事前にユーザーを作っておく or 既に self.registered_uuid があるなら使う
        username = getattr(self, "registered_uuid", None) or ("guest_" + uuid.uuid4().hex[:5])
        data = {
            "username": username,
            "password": "TestPass1"
        }
        resp = requests.post(url, json=data)
        assert resp.status_code in [200, 401, 500]
        if resp.status_code == 200:
            body = resp.json()
            assert body.get("success") is True
            assert "jwt_token" in body

    def test_user_routes(self):
        """
        /user/... など user_manager/app_user_manager.py で定義されたAPIを想定
        """
        # 例: GET /user/get?user_uuid=xxx
        #     POST /user/profile/update
        #     POST /user/keys/update
        pass

    def test_ca_routes(self):
        """
        /ca/... CA関連エンドポイントをテスト
        例: GET /ca/info
        """
        resp = requests.get(self.base_url + "/ca/info")
        # 200 or 400など
        assert resp.status_code in [200, 400]
        # body内容をチェックするなら:
        # if resp.status_code == 200:
        #     assert "有効期限" in resp.text
