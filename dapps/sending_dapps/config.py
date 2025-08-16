# dapps/sending_dapps/config.py
"""
送信用 DApp の設定
"""
import os

# AWS の Region
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# ユーザー登録情報を保持している DynamoDB テーブル名
# register_bp を通じて登録済みのユーザーをここから取得します
USERS_TABLE = os.getenv("USERS_TABLE", "UsersTable")

# 大陸ごとの DAG 登録サーバー URL (実運用では環境変数等で管理してください)
REGION_SERVERS = {
    "asia":    "https://asia.dag.example.com",
    "europe":  "https://europe.dag.example.com",
    "america": "https://america.dag.example.com",
}

# 国コード → 大陸マッピング
COUNTRY_TO_CONTINENT = {
    "JP": "asia",
    "CN": "asia",
    "KR": "asia",
    "US": "america",
    "CA": "america",
    "DE": "europe",
    "FR": "europe",
    # 必要に応じて追加
}

# DAG 登録 API のパス
DAG_API_PATH = "/api/dag/add_transaction"
