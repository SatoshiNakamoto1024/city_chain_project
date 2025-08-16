# D:\city_chain_project\network\DAGs\common\storage_service\config.py
"""
storage_service.config
----------------------
環境変数で上書き可能なデフォルト設定
"""
from __future__ import annotations
import os

# gRPC サーバーポート
SERVER_PORT: int = int(os.getenv("STORAGE_PORT", 50061))

# ファイル保存ベースパス（フォールバック実装で使用）
STORAGE_BASE: str = os.getenv("STORAGE_BASE", "./storage_data")

# ログレベル
LOG_LEVEL: str = os.getenv("STORAGE_LOGLEVEL", "INFO").upper()
