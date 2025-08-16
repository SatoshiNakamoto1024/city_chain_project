import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
import json
import glob
from datetime import datetime
from CA.app_ca import app, table, S3_BUCKET, LOCAL_CERT_STORAGE, LOCAL_METADATA_STORAGE
import boto3

class CATestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Clear DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
        scan = table.scan()
        with table.batch_writer() as batch:
            for item in scan.get("Items", []):
                # テーブルのスキーマが複合キーの場合、"uuid" と "session_id" の両方を指定
                if "uuid" in item and "session_id" in item:
                    batch.delete_item(Key={"uuid": item["uuid"], "session_id": item["session_id"]})

        # Clear S3 objects under "ca_cert/"
        s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="ca_cert/")
        if "Contents" in response:
            for obj in response["Contents"]:
                s3.delete_object(Bucket=S3_BUCKET, Key=obj["Key"])

        # Clear local directories
        for directory in [LOCAL_METADATA_STORAGE, LOCAL_CERT_STORAGE]:
            files = glob.glob(os.path.join(directory, "*"))
            for f in files:
                os.remove(f)

    def test_issue_certificate(self):
        uuid_val = "ca-test-uuid-001"
        response = self.app.get(f"/issue_cert?uuid={uuid_val}&validity_days=30")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode("utf-8"))
        self.assertIn("client_cert", data)
        self.assertIn("fingerprint", data)
        # Check DynamoDB metadata exists
        db_response = table.get_item(Key={"uuid": uuid_val, "session_id": "CLIENT_CERT"})
        self.assertIn("Item", db_response)
        db_item = db_response["Item"]
        self.assertEqual(db_item.get("uuid"), uuid_val)
        self.assertFalse(db_item.get("revoked"))
        # Check local files exist
        metadata_files = glob.glob(os.path.join(LOCAL_METADATA_STORAGE, f"{uuid_val}_*.json"))
        cert_files = glob.glob(os.path.join(LOCAL_CERT_STORAGE, f"{uuid_val}_*.json"))
        self.assertTrue(len(metadata_files) > 0)
        self.assertTrue(len(cert_files) > 0)

    def test_revoke_certificate(self):
        uuid_val = "ca-test-uuid-002"
        self.app.get(f"/issue_cert?uuid={uuid_val}")
        revoke_response = self.app.post("/revoke_cert", data=json.dumps({"uuid": uuid_val}),
                                          content_type="application/json")
        self.assertEqual(revoke_response.status_code, 200)
        revoke_data = json.loads(revoke_response.data.decode("utf-8"))
        self.assertTrue(revoke_data.get("revoked"))
        self.assertIsNotNone(revoke_data.get("revoked_at"))
        # Check DynamoDB updated
        db_response = table.get_item(Key={"uuid": uuid_val, "session_id": "CLIENT_CERT"})
        db_item = db_response["Item"]
        self.assertTrue(db_item.get("revoked"))
        self.assertIsNotNone(db_item.get("revoked_at"))
        # Check local files updated
        metadata_files = glob.glob(os.path.join(LOCAL_METADATA_STORAGE, f"{uuid_val}_*.json"))
        for fpath in metadata_files:
            with open(fpath, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            self.assertTrue(metadata.get("revoked"))
            self.assertIsNotNone(metadata.get("revoked_at"))
    
    def test_list_certificates(self):
        uuid_vals = ["ca-test-uuid-003", "ca-test-uuid-004"]
        for uid in uuid_vals:
            self.app.get(f"/issue_cert?uuid={uid}")
        list_response = self.app.get("/list_cert")
        self.assertEqual(list_response.status_code, 200)
        cert_list = json.loads(list_response.data.decode("utf-8"))
        for uid in uuid_vals:
            self.assertTrue(any(item.get("uuid") == uid for item in cert_list))

if __name__ == '__main__':
    unittest.main()
