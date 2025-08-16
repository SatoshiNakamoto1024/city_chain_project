# user_manager/config.py
import os

# ユーザー管理用基本設定

# AWS/DynamoDB/S3 の設定（auth_py/config.py と共通化する場合もある）
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")  # ←これが必要！
S3_BUCKET = os.getenv("S3_BUCKET", "my-resister-bucket-2025")
USERS_TABLE = os.getenv("USERS_TABLE", "UsersTable")
STORAGE_USAGE_TABLE = os.getenv("STORAGE_USAGE_TABLE", "StorageUsageTable")

# 連絡先などの必須フィールド
REQUIRED_FIELDS = ["name", "birth_date", "address", "mynumber", "email", "phone", "password"]

# パスワード更新時の最小文字数
MIN_PASSWORD_LENGTH = 8

# マイナンバーの桁数（例:12桁）
MYNUMBER_LENGTH = 12
