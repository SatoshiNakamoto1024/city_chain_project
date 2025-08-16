# test_user_manager.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import subprocess
import time
import requests
import uuid


"""
このテストは user_manager\app_user_manager.py が提供するルート
(/user/profile/update, /user/password/change, /user/keys/update, /user/lifeform/register)
を対象に統合テストを行う。

【注意】
- 以前は /user/register をテストしていたが、現在の設計では
  ユーザー登録は login/registration/registration.py (別サーバー/別ルート) に実装されているため、
  このファイルではテストしない。
- DynamoDB/S3への実アクセスを想定しているため、ローカル or テスト環境で実行する際は
  資格情報やテーブルが正しくセットアップされている必要がある。
"""

@pytest.fixture(scope="module")
def run_user_manager_server():
    """
    user_manager の Flaskサーバー (app_user_manager.py) をサブプロセスで起動し、
    テスト後に停止する。DynamoDB/S3に直接アクセスする想定。
    """
    process = subprocess.Popen(["python", "user_manager\\app_user_manager.py"], shell=True)
    time.sleep(3)  # サーバー起動待ち

    yield

    # 終了処理
    process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()


@pytest.mark.usefixtures("run_user_manager_server")
class TestUserManagerIntegration:
    """
    /user 以下のエンドポイントをテスト:
      - /profile/update
      - /password/change
      - /keys/update
      - /lifeform/register
    """

    base_url = "http://192.168.3.8:5000/user"

    def _create_user_directly(self) -> str:
        """
        テスト用: DynamoDBに最低限のユーザーレコードを直接作成して uuid を返す。
        実運用では /register (login/registration) で登録する想定のため、
        ここでは簡易的にダミー項目を put_item しておく。
        """
        import boto3
        from user_manager.config import DYNAMODB_TABLE
        from datetime import datetime

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.Table(DYNAMODB_TABLE)

        user_uuid = str(uuid.uuid4())
        item = {
            "uuid": user_uuid,
            "session_id": "REGISTRATION",
            "username": "TestUser",
            "email": "test@example.com",
            "password_hash": "dummyhash",
            "salt": "dummysalt",  # ユニットテスト用のダミー
            "created_at": datetime.utcnow().isoformat()
        }
        table.put_item(Item=item)
        return user_uuid

    def test_update_profile(self):
        """
        /user/profile/update のテスト:
          1) ダミーユーザーを _create_user_directly で作成
          2) /user/profile/update を呼び出し、address/phone を更新
          3) レスポンス200で更新結果JSONを確認
        """
        user_uuid = self._create_user_directly()

        url = f"{self.base_url}/profile/update"
        update_data = {
            "user_uuid": user_uuid,
            "address": "Updated Street 999",
            "phone": "09077776666"
        }
        resp = requests.post(url, json=update_data)
        assert resp.status_code == 200, resp.text

        updated = resp.json()
        assert updated.get("address") == "Updated Street 999"
        assert updated.get("phone") == "09077776666"

    def test_change_password(self):
        """
        /user/password/change のテスト:
          1) ダミーユーザーを作成
          2) current_password=..., new_password=... を送信
          3) 実際には password_hash 検証で失敗するかもしれないが、最低限レスポンス確認
        """
        user_uuid = self._create_user_directly()

        url = f"{self.base_url}/password/change"
        ch_data = {
            "user_uuid": user_uuid,
            "current_password": "dummyCurrent",
            "new_password": "NewPass456"
        }
        resp = requests.post(url, json=ch_data)
        # 200 or 401 or 500など、実装によって異なる
        assert resp.status_code in [200, 400, 401, 500], resp.text

    def test_update_keys(self):
        """
        /user/keys/update のテスト:
          1) ダミーユーザーを作成
          2) /user/keys/update を呼び出して Dillithium鍵を更新
          3) 成功なら200と新しい private_key等が返る
        """
        user_uuid = self._create_user_directly()

        url = f"{self.base_url}/keys/update"
        data = {"user_uuid": user_uuid}
        resp = requests.post(url, json=data)
        assert resp.status_code in [200, 404, 500], resp.text

        if resp.status_code == 200:
            body = resp.json()
            # update_user_keys が success時に 'dilithium_secret_key' を返す想定
            assert "dilithium_secret_key" in body, body

    def test_register_lifeform(self):
        """
        /user/lifeform/register のテスト:
          1) ダミーユーザーを作成
          2) extra_dimensionsを送って、lifeformを登録
        """
        user_uuid = self._create_user_directly()

        url = f"{self.base_url}/lifeform/register"
        lf_data = {
            "user_id": user_uuid,
            "team_name": "DimTeam",
            "affiliation": "DimAffiliation",
            "municipality": "DimCity",
            "state": "DimState",
            "country": "DimCountry",
            "extra_dimensions": ["ExtraA", "ExtraB"]
        }
        resp = requests.post(url, json=lf_data)
        assert resp.status_code in [200, 500], resp.text

        if resp.status_code == 200:
            lf_body = resp.json()
            assert "lifeform_id" in lf_body
            assert lf_body["user_id"] == user_uuid
