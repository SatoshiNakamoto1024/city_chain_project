# login/config.py

import os

# AWS Settings
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
USER_TABLE = os.getenv("USER_TABLE", "UsersTable")
S3_BUCKET = os.getenv("S3_BUCKET", "my-resister-bucket-2025")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:UserNotifications")

# MongoDB Settings (未使用なら削除可)
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "federation_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "users")

# JWT設定
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_key")

# パスワードソルトサイズ
PASSWORD_SALT_SIZE = 16

# その他ログイン関連
QR_CODE_EXPIRATION = 300  # (秒)

# Flask基本設定
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "5000"))
DEBUG = True
