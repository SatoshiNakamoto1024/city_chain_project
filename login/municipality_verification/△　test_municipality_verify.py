import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import unittest
import uuid
import json
from datetime import datetime, timezone
import boto3
import time

# ✅ テスト対象のパスを登録
ROOT_PATH = r"D:\city_chain_project\login"
AUTH_PY_PATH = os.path.join(ROOT_PATH, "auth_py")
LOGIN_APP_PATH = os.path.join(ROOT_PATH, "login_app")

if AUTH_PY_PATH not in sys.path:
    sys.path.insert(0, AUTH_PY_PATH)
if LOGIN_APP_PATH not in sys.path:
    sys.path.insert(0, LOGIN_APP_PATH)

# ✅ 必要な定数を config から読み込む
from config import DYNAMODB_TABLE, AWS_REGION

# ✅ JWT生成用
from auth import generate_jwt

# ✅ テスト対象の関数をインポート
from login_app.municipality_verification.verification import approve_user
from login_app.municipality_verification.admin_tools.approval_logger import log_approval

# DynamoDB テーブル設定
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(DYNAMODB_TABLE)
approval_log_table = dynamodb.Table("MunicipalApprovalLogTable")

# ダミーの職員JWT（本番では verify_admin_jwt による検証想定）
DUMMY_ADMIN_JWT = generate_jwt("admin-test-user")

class MunicipalityVerificationTest(unittest.TestCase):

    def setUp(self):
        self.test_uuid = str(uuid.uuid4())
        self.test_session_id = str(uuid.uuid4())

        # DynamoDB に仮ユーザー登録
        self.test_user = {
            "uuid": self.test_uuid,
            "session_id": self.test_session_id,  # Sort Key 必須ならここで指定
            "username": "test_user_verify",
            "email": "verify@example.com",
            "password_hash": "dummyhash",
            "salt": "dummysalt",
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        users_table.put_item(Item=self.test_user)

    def test_approve_user_and_log(self):
        # Step 1: ユーザー承認（UsersTable 更新）
        approve_user(self.test_uuid)

        # Step 2: 承認ログ記録
        log_approval(
            uuid=self.test_uuid,
            approver_id="admin-test-user",
            action="approved",
            reason="本人確認OK",
            client_ip="127.0.0.1"
        )

        # 非同期対策のため少し待つ
        time.sleep(1)

        # Step 3: 承認後のステータス確認
        res = users_table.get_item(Key={
            "uuid": self.test_uuid,
            "session_id": self.test_session_id
        })
        self.assertIn("Item", res)
        self.assertEqual(res["Item"]["status"], "approved")

        # Step 4: ログの確認
        log_query = approval_log_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("uuid").eq(self.test_uuid),
            ScanIndexForward=False,
            Limit=1
        )
        logs = log_query.get("Items", [])
        self.assertTrue(logs)
        latest_log = logs[0]
        self.assertEqual(latest_log["action"], "approved")
        self.assertEqual(latest_log["approver_id"], "admin-test-user")

        print("✅ ユーザー承認 & 承認ログ記録 成功")

    def tearDown(self):
        # ユーザー削除
        users_table.delete_item(Key={
            "uuid": self.test_uuid,
            "session_id": self.test_session_id
        })

        # ログ削除（timestamp 不明のため scan）
        items = approval_log_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("uuid").eq(self.test_uuid)
        ).get("Items", [])
        for item in items:
            approval_log_table.delete_item(
                Key={
                    "uuid": item["uuid"],
                    "timestamp": item["timestamp"]
                }
            )

if __name__ == "__main__":
    unittest.main()
