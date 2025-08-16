# municipality_verification/config.py

import os

# ==========================
# Flask の基本設定
# ==========================
DEBUG = True
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 5000))
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# ==========================
# セッション設定
# ==========================
SESSION_COOKIE_NAME       = "login_session"
PERMANENT_SESSION_LIFETIME = 3600  # 秒

# ==========================
# API 設定
# ==========================
API_BASE_URL = "http://localhost:5000/api"

# ==========================
# JWT 設定
# ==========================
JWT_SECRET           = os.getenv("JWT_SECRET", "my_jwt_secret_2025")
JWT_ALGORITHM        = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "1"))  # 1時間

# ==========================
# AWS リージョン & S3 設定
# ==========================
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET  = os.getenv("S3_BUCKET", "my-register-bucket-2025")

# ==========================
# DynamoDB テーブル名
# ==========================
USERS_TABLE         = os.getenv("USERS_TABLE", "UsersTable")           # 住民テーブル
STAFF_TABLE         = os.getenv("STAFF_TABLE", "MunicipalStaffs")      # 職員サマリテーブル
ADMIN_TABLE         = os.getenv("ADMIN_TABLE", "AdminsTable")          # admin 用サマリ
DEVICES_TABLE       = os.getenv("DEVICES_TABLE", "DevicesTable")
APPROVAL_LOG_TABLE  = os.getenv("APPROVAL_LOG_TABLE", "MunicipalApprovalLogTable")
LOGIN_HISTORY       = os.getenv("LOGIN_HISTORY", "LoginHistory")

# ==========================
# その他認証・暗号設定
# ==========================
PASSWORD_SALT_SIZE = 16  # ソルトバイト長
