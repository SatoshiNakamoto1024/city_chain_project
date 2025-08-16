# login/auth_py/config.py
import os
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# AWS Settings (ダミー値・実際の環境変数で上書き可能)
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "UsersTable")
WALLETS_TABLE = os.getenv("WALLETS_TABLE", "WalletsTable")
LOGIN_HISTORY = os.getenv("LOGIN_HISTORY", "LoginHistory")
S3_BUCKET = os.getenv("S3_BUCKET", "my-resister-bucket-2025")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:235494777820:DevNotificationTopic")
USERS_TABLE_NAME = os.getenv("USERS_TABLE_NAME", "UsersTable")

# JWT設定
JWT_SECRET           = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET_IN_PROD")
JWT_ALGORITHM        = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "1"))

PASSWORD_SALT_BYTES = int(os.getenv("PASSWORD_SALT_BYTES", "16"))
# ← これを既存 password_manager.py が期待する名前でもエクスポート
PASSWORD_SALT_SIZE  = PASSWORD_SALT_BYTES

# QRコード有効期限（秒）
QR_CODE_EXPIRATION   = int(os.getenv("QR_CODE_EXPIRATION", "300"))
