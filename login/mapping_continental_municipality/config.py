# mapping_continental_municipality/config.py

import os

# ======================================
# DynamoDB テーブル名
# ======================================
USER_LOCATION_TABLE = os.getenv("USER_LOCATION_TABLE", "UserLocationMapping")

# ======================================
# AWS リージョン設定
# ======================================
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
