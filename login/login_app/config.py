# login_app/config.py

import os

# Flaskの基本設定
DEBUG = True
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 6010))
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# セッション設定
SESSION_COOKIE_NAME = "login_session"
PERMANENT_SESSION_LIFETIME = 3600  # 秒
JWT_SECRET                 = os.getenv("JWT_SECRET", "my_jwt_secret")

# API ベースURL（必要に応じて）
API_BASE_URL = "http://localhost:5000/api"

# 初期付与トークン数（仮）
INITIAL_HARMONY_TOKEN = 100

# AWS 連携設定
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "my-resister-bucket-2025")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "UsersTable")
USERS_TABLE = os.getenv("USERS_TABLE", "UsersTable")  # デフォルトはUsersTable
LOGIN_HISTORY_TB = os.getenv("LOGIN_HISTORY_TABLE", "LoginHistory")
CLIENT_CERT_TB = os.getenv("CLIENT_CERT_TABLE", "ClientCertificates")

# S3 (証明書 json が置いてあるバケット – フェーズ 1 と共通)
CERT_BUCKET = os.getenv("S3_BUCKET", "my-client-cert-bucket")

# クライアント証明書サービスのベース URL
# 開発環境では localhost:6001、本番ならコンテナ名 or ELB
CLIENT_CERT_ENDPOINT = os.getenv(
    "CLIENT_CERT_ENDPOINT",
    "http://localhost:6001/client_cert"
)
