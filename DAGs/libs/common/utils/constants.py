# もし将来的に定数が増えたら、ここに constants.py を追加するとよいでしょう。
# network/DAGs/common/utils/constants.py
"""
共通定数定義
"""
# ── DAG 関連
MAX_DAG_NODES: int = 1000
DEFAULT_RETRY_ATTEMPTS: int = 3
DEFAULT_BACKOFF_SECONDS: float = 0.2

# ── ストレージ関連
SHARD_SIZE_LIMIT: int = 100 * 1024 * 1024  # 100 MB
