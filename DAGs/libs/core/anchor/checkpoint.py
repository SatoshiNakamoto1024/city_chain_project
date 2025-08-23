# network/DAGs/dag/anchor/checkpoint.py

import uuid
from typing import Dict, Any


class CheckpointManager:
    """
    各バッチ完了時に一意の checkpoint_id を生成・管理するクラス。
    """
    def __init__(self):
        # in-memory cache 例。必要なら外部ストレージに置き換え。
        self._store: Dict[str, Dict[str, Any]] = {}

    def create_checkpoint(self, dag_id: str, metadata: Dict[str, Any]) -> str:
        """
        新規チェックポイントを作成し、ID を返す。
        """
        cp_id = str(uuid.uuid4())
        self._store[cp_id] = {
            "dag_id": dag_id,
            "metadata": metadata,
            "timestamp": metadata.get("timestamp"),
        }
        return cp_id

    def get_checkpoint(self, cp_id: str) -> Dict[str, Any]:
        """
        保存済 checkpoint の情報を取得。
        """
        return self._store.get(cp_id, {})
