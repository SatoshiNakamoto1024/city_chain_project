import os
import sys
import unittest
import json
import glob
import uuid
import time
import boto3
from datetime import datetime

# パスを通す
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Flask テスト用アプリケーション
from client_cert.app_client_cert import (
    create_app,
    S3_BUCKET,
    LOCAL_METADATA_DIR,
    LOCAL_CERT_DIR,
)
from client_cert.table import table  # DynamoDB テーブルオブジェクト

# API直テスト用
from client_cert_api import app as api_app

# AWS 環境変数
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("S3_BUCKET", "my-client-cert-bucket")
os.environ.setdefault("DYNAMODB_TABLE", "ClientCertificates")

AWS_REGION = os.getenv("AWS_REGION")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")


class ClientCertTestCase(unittest.TestCase):
    def setUp(self):
        # 通常の Flask クライアント
        self.app = create_app().test_client()
        self.api = api_app.test_client()
        self.app.testing = True
        self.api.testing = True

        # DynamoDB 初期化
        scan = table.scan()
        with table.batch_writer() as batch:
            for item in scan.get("Items", []):
                batch.delete_item(Key={"uuid": item["uuid"], "session_id": item["session_id"]})
        print("[DEBUG] Cleared DynamoDB table.")

        # S3 初期化
        s3 = boto3.client("s3", region_name=AWS_REGION)
        resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="client_cert/")
        if "Contents" in resp:
            for obj in resp["Contents"]:
                s3.delete_object(Bucket=S3_BUCKET, Key=obj["Key"])
        print("[DEBUG] Cleared S3")

        # ローカル初期化
        for d in (LOCAL_METADATA_DIR, LOCAL_CERT_DIR):
            for f in glob.glob(os.path.join(d, "*")):
                os.remove(f)
        print("[DEBUG] Cleared local dirs.")

    def test_ntru_dilithium_full_certificate_flow(self):
        """NTRU + Dilithium を含む証明書発行の全体テスト"""
        user_id = str(uuid.uuid4())

        # クライアント証明書を発行
        res = self.api.post("/issue_cert", json={"uuid": user_id})
        self.assertEqual(res.status_code, 200)

        data = json.loads(res.data)
        cert = data.get("certificate")

        self.assertIn("uuid", cert)
        self.assertIn("ntru_public", cert)
        self.assertIn("dilithium_public", cert)
        self.assertIn("valid_from", cert)
        self.assertIn("valid_to", cert)
        self.assertIn("signature", cert)

        # 鍵ペアが存在するか
        self.assertIn("ntru_private", data)
        self.assertIn("dilithium_private", data)

        # JSON形式として保存しても正常にパースできるか
        cert_json = json.dumps(cert, indent=2, ensure_ascii=False)
        self.assertTrue(isinstance(cert_json, str))

    def test_generate_and_revoke_flow(self):
        """通常発行 + 失効 + 確認までのフロー"""
        uid = str(uuid.uuid4())
        r = self.app.get(f"/client_cert?uuid={uid}&validity_days=60")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn("fingerprint", data)

        # DynamoDB 確認
        time.sleep(1)
        item = table.get_item(Key={"uuid": uid, "session_id": "CLIENT_CERT"}).get("Item")
        self.assertIsNotNone(item)
        self.assertFalse(item["revoked"])

        # 証明書失効
        r2 = self.app.post("/revoke_cert", json={"uuid": uid})
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(json.loads(r2.data)["revoked"])

        # 確認
        r3 = self.app.get(f"/check_cert?uuid={uid}")
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(json.loads(r3.data)["revoked"])

    def test_list_cert_contains_all(self):
        """複数の証明書が list_cert に表示されるか"""
        ids = [str(uuid.uuid4()) for _ in range(3)]
        for uid in ids:
            self.app.get(f"/client_cert?uuid={uid}")
        r = self.app.get("/list_cert")
        self.assertEqual(r.status_code, 200)
        listed = json.loads(r.data)
        for uid in ids:
            self.assertTrue(any(i["uuid"] == uid for i in listed))

    def test_download_certificate(self):
        """発行後に /download_cert から取得できるか"""
        uid = str(uuid.uuid4())
        self.app.get(f"/client_cert?uuid={uid}")
        r = self.app.get(f"/download_cert?uuid={uid}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.data)["uuid"], uid)

    def test_missing_params(self):
        """uuidパラメータ欠落時のエラーハンドリング"""
        r1 = self.app.get("/client_cert")
        self.assertEqual(r1.status_code, 400)

        r2 = self.app.get("/download_cert")
        self.assertEqual(r2.status_code, 400)

        r3 = self.app.post("/revoke_cert", json={})
        self.assertEqual(r3.status_code, 400)

    def test_debug_scan_items(self):
        print("=== DynamoDB Items ===")
        items = table.scan().get("Items", [])
        for item in items:
            print(item)


if __name__ == "__main__":
    unittest.main()
