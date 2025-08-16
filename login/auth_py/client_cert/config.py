# auth_py/client_cert/config.py
import sys
import os
# sys.path.append(os.path.abspath(os.path.dirname(__file__))) 
import boto3  # ← ここを追加

# CA 設定
CA_NAME = os.getenv("CA_NAME", "MyProductionCA")
DEFAULT_VALIDITY_DAYS = int(os.getenv("DEFAULT_VALIDITY_DAYS", "365"))

# HSM（ハードウェアセキュリティモジュール）の設定（ダミー）
HSM_ENABLED = os.getenv("HSM_ENABLED", "False") == "True"
HSM_CONFIG = {
    "device": os.getenv("HSM_DEVICE", "dummy_hsm"),
    "pin": os.getenv("HSM_PIN", "0000")
}

# AWS 設定（本番環境用）
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "my-ca-bucket-2025")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "ClientCertificates")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)