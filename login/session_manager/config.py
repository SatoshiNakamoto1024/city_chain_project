# session_manager/config.py
import os

# セッション管理用設定

# DynamoDB の LoginHistory テーブル名（実際は環境変数で上書き可能）
LOGIN_HISTORY_TABLE = os.getenv("LOGIN_HISTORY_TABLE", "LoginHistory")

# セッション保持期間のデフォルト（例: 30日）
SESSION_RETENTION_DAYS = int(os.getenv("SESSION_RETENTION_DAYS", "30"))