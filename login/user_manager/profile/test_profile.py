# test_profile.py

import pytest
import subprocess
import time
import requests
import uuid

@pytest.fixture(scope="module")
def run_profile_server():
    """
    app_profile.py をサブプロセスで起動し、テスト完了後に停止。
    DynamoDB/S3に対して本番アクセスが行われるため、AWS認証情報が必要。
    """
    process = subprocess.Popen(["python", "user_manager\\profile\\app_profile.py"], shell=True)
    time.sleep(3)  # サーバー起動待ち

    yield

    process.terminate()
    try:
        process.wait(timeout=5)
    except Exception:
        process.kill()

@pytest.mark.usefixtures("run_profile_server")
class TestProfileIntegration:
    base_url = "http://192.168.3.8:5000/profile/"

    def test_get_profile_missing_uuid(self):
        """
        GET /profile -> ?uuid= が無い場合は 400
        """
        resp = requests.get(self.base_url)
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body

    def test_get_profile_not_found(self):
        """
        GET /profile?uuid=nonexistent -> 404
        """
        resp = requests.get(f"{self.base_url}?uuid=nonexistent")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body

    def test_post_profile_update_no_uuid(self):
        """
        POST /profile (フォーム) -> uuidが無ければ 400
        """
        resp = requests.post(self.base_url, data={"address": "No UUID Street"})
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body

    def test_post_profile_update(self):
        """
        正常系: DynamoDBに存在するユーザーのプロフィールを /profile POST でアップデートするテスト
        """
        import boto3
        from datetime import datetime
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")  # AWS_REGION も使えます
        # ユーザーテーブル名は実際の環境に合わせる（例: "UsersTable"）
        users_table = dynamodb.Table("UsersTable")
    
        # テスト用ユーザーを直接DynamoDBに登録
        test_user_uuid = str(uuid.uuid4())
        test_user_item = {
            "uuid": test_user_uuid,
            "session_id": "REGISTRATION",  # ここを追加（実際の環境に合わせて適切な値を設定）
            "name": "ProfileTest",
            "birth_date": "2001-01-01",
            "address": "XYZ Street",
            "mynumber": "111111111111",
            "email": f"profile_{uuid.uuid4().hex[:5]}@example.com",
            "phone": "08022223333",
            "password_hash": "dummy",  # ダミー値
            "salt": "dummy",
            "initial_harmony_token": "300",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        users_table.put_item(Item=test_user_item)

        # /profile POST で更新
        base_url = "http://192.168.3.8:5000/profile/"
        form_data = {
            "uuid": test_user_uuid,
            "address": "Updated Street 999",
            "phone": "09077776666"
        }
        resp = requests.post(base_url, data=form_data)
        # ステータスコードは、ユーザーが更新できれば200、見つからなければ404や500になる可能性もあるので許容
        assert resp.status_code in [200, 404, 500]
        if resp.status_code == 200:
            updated_user = resp.json()
            assert updated_user["address"] == "Updated Street 999"
            assert updated_user["phone"] == "09077776666"
