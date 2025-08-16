# login/wallet/config.py
"""
login.wallet – 共通設定

❏ ここを単独で import すれば、他モジュールからも
   ・AWS_REGION
   ・WALLET_TABLE / USERS_TABLE
   ・S3_BUCKET など
   を一か所で参照できる。
"""

import os
from pathlib import Path

# ─────────────────────────────────────
#  AWS / DynamoDB / S3 / SNS
# ─────────────────────────────────────
AWS_REGION   = os.getenv("AWS_REGION",   "us-east-1")

# DynamoDB テーブル
WALLET_TABLE = os.getenv("WALLET_TABLE", "WalletsTable")   # ← ウォレット専用
USERS_TABLE  = os.getenv("USERS_TABLE",  "UsersTable")     # 既存ユーザーテーブル

# S3 (バックアップや証明書保存等に使用する場合)
S3_BUCKET    = os.getenv("S3_BUCKET",    "my-resister-bucket-2025")

# 通知を飛ばす場合の SNS
SNS_TOPIC_ARN = os.getenv(
    "SNS_TOPIC_ARN",
    "arn:aws:sns:us-east-1:123456789012:UserNotifications"
)

# ─────────────────────────────────────
#  MongoDB（フェデレーション用 – 使わないなら無視）
# ─────────────────────────────────────
MONGODB_URI     = os.getenv("MONGODB_URI",    "mongodb://localhost:27017/")
DATABASE_NAME   = os.getenv("DATABASE_NAME",  "federation_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME","users")

# ─────────────────────────────────────
#  セキュリティ
# ─────────────────────────────────────
JWT_SECRET         = os.getenv("JWT_SECRET",        "your_jwt_secret_key")
PASSWORD_SALT_SIZE = int(os.getenv("PASSWORD_SALT_SIZE", 16))

# QR コードの有効期限（秒）
QR_CODE_EXPIRATION = int(os.getenv("QR_CODE_EXPIRATION", 300))

# ─────────────────────────────────────
#  Flask / サービス基本設定
# ─────────────────────────────────────
HOST  = os.getenv("HOST",  "0.0.0.0")
PORT  = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")

# ─────────────────────────────────────
#  便利: ルートディレクトリなど
# ─────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent   # login/ まで
CERT_DIR = BASE_DIR / "certs"
CERT_DIR.mkdir(exist_ok=True)
