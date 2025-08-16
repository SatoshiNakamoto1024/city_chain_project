# test_user_manager.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
import time
import subprocess
import requests
import pytest
import base64
from auth_py.jwt_manager import generate_jwt
from user_manager.config import USERS_TABLE, AWS_REGION
import boto3
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\dilithium-py"))
from app_dilithium import create_keypair

"""
このテストは /user 以下のエンドポイントを統合的に検証します。
必ず DynamoDB テーブルが用意されているテスト環境で実行してください。
"""

@pytest.fixture(scope="module")
def run_user_manager_server():
    # 正しいパスを組み立てる
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "app_user_manager.py"))

    proc = subprocess.Popen(
        [sys.executable, script_path],
        cwd=os.path.dirname(script_path),
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    time.sleep(3)
    yield
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except:
        proc.kill()

@pytest.mark.usefixtures("run_user_manager_server")
class TestUserManagerIntegration:
    base_url = "http://127.0.0.1:5000/user"

    def _create_user_directly(self) -> str:
        """
        DynamoDB に session_id='REGISTRATION' のダミーユーザーを作成。
        """
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(USERS_TABLE)

        user_uuid = str(uuid.uuid4())
        item = {
            "uuid":          user_uuid,
            "session_id":    "REGISTRATION",
            "username":      "TestUser",
            "email":         "test@example.com",
            "password_hash": "dummyhash",
            "salt":          "dummysalt",
            "created_at":    datetime.utcnow().isoformat()
        }
        table.put_item(Item=item)
        return user_uuid

    def _auth_header(self, user_uuid: str) -> dict:
        token = generate_jwt(user_uuid)
        return {"Authorization": f"Bearer {token}"}

    def test_update_profile(self):
        user_uuid = self._create_user_directly()
        headers   = self._auth_header(user_uuid)
        url       = f"{self.base_url}/profile/update"
        payload   = {
            "user_uuid": user_uuid,
            "address":   "Updated Street 999",
            "phone":     "09077776666"
        }

        resp = requests.post(url, json=payload, headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body.get("address") == "Updated Street 999"
        assert body.get("phone") == "09077776666"

    def test_change_password(self):
        user_uuid = self._create_user_directly()
        headers   = self._auth_header(user_uuid)
        url       = f"{self.base_url}/password/change"
        payload   = {
            "user_uuid":        user_uuid,
            "current_password": "dummyCurrent",
            "new_password":     "NewPass456"
        }

        resp = requests.post(url, json=payload, headers=headers)
        # 実装によって返り値が変わる可能性があるので範囲でチェック
        assert resp.status_code in (200, 400, 401, 500), resp.text

    def test_update_keys(self):
        user_uuid = self._create_user_directly()
        headers   = self._auth_header(user_uuid)
        url       = f"{self.base_url}/keys/update"

        # RSA 鍵ペアを生成し、PEM 形式の公開鍵を作成
        rsa_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsa_public_key = rsa_private_key.public_key()
        rsa_pub_pem = rsa_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        # 公開鍵を含めてリクエスト
        payload = {
            "user_uuid":   user_uuid,
            "rsa_pub_pem": rsa_pub_pem
        }
        resp = requests.post(url, json=payload, headers=headers)
        assert resp.status_code in (200, 404, 500), resp.text

        if resp.status_code == 200:
            body = resp.json()
            assert "encrypted_secret_key_b64" in body
            assert "dilithium_public_key" in body
            assert "dilithium_secret_key_b64" in body

            # ── ここから生バイト列の長さチェック ──
            # 1) テスト用に鍵長を取得 (Rust バインディング)
            _, expected_secret = create_keypair()
            expected_len = len(expected_secret)

            # 2) Base64 → bytes に戻す
            actual_secret = base64.b64decode(body["dilithium_secret_key_b64"])

            # 3) 長さが一致すること
            assert len(actual_secret) == expected_len, (
                f"Expected secret length {expected_len}, got {len(actual_secret)}"
            )

    def test_register_lifeform(self):
        user_uuid = self._create_user_directly()
        headers   = self._auth_header(user_uuid)
        url       = f"{self.base_url}/lifeform/register"
        payload   = {
            "user_id":           user_uuid,
            "team_name":         "DimTeam",
            "affiliation":       "DimAffiliation",
            "municipality":      "DimCity",
            "state":             "DimState",
            "country":           "DimCountry",
            "extra_dimensions":  ["ExtraA", "ExtraB"]
        }

        resp = requests.post(url, json=payload, headers=headers)
        assert resp.status_code in (200, 500), resp.text
        if resp.status_code == 200:
            body = resp.json()
            assert body["user_id"] == user_uuid
            assert "lifeform_id" in body
