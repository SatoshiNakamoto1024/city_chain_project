# CA/config.py
import sys
import os
# sys.path.append(os.path.abspath(os.path.dirname(__file__))) 

# CA 設定
CA_NAME = os.getenv("CA_NAME", "MyProductionCA")
DEFAULT_VALIDITY_DAYS = int(os.getenv("DEFAULT_VALIDITY_DAYS", "365"))

# HSM（ハードウェアセキュリティモジュール）の設定（ダミー）
HSM_ENABLED = os.getenv("HSM_ENABLED", "False") == "True"
HSM_CONFIG = {
    "device": os.getenv("HSM_DEVICE", "dummy_hsm"),
    "pin": os.getenv("HSM_PIN", "0000")
}

# ローカル保存先の設定（CA 管理用）
LOCAL_CERT_STORAGE = os.getenv("LOCAL_CERT_STORAGE", r"D:\city_chain_project\CA\certs")
LOCAL_METADATA_STORAGE = os.getenv("LOCAL_METADATA_STORAGE", r"D:\city_chain_project\CA\metadata")

# AWS 設定（本番環境用）
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "my-ca-bucket-2025")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "CACertificates")
