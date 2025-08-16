# registration/config.py

import os

# Flask の基本設定
DEBUG = True
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 5000))
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# セッション設定
SESSION_COOKIE_NAME = "login_session"
PERMANENT_SESSION_LIFETIME = 3600  # 秒

# API ベース URL（必要に応じて）
API_BASE_URL = "http://localhost:5000/api"

# 初期付与トークン数（仮）
INITIAL_HARMONY_TOKEN = 100

# AWS 連携設定
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "my-resister-bucket-2025")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "UsersTable")
DEVICES_TABLE = os.getenv("DEVICES_TABLE", "DevicesTable")
PAIRING_TOKEN_TABLE = os.getenv("PAIRING_TOKEN_TABLE", "PairingTokensTable")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:235494777820:DevNotificationTopic")

# JWT 設定
JWT_SECRET = os.getenv("JWT_SECRET", "my_jwt_secret")
