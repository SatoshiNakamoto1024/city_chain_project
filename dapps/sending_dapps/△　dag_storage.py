# sending_dapps/dag_storage.py
"""
非同期 DAG 保存処理ユーティリティ。

CityDAGHandler を使ってトランザクションを分散型台帳に投げ込む部分を
将来的にここにまとめます。
"""

import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DAGStorage:
    """
    CityDAGHandler のラッパークラス。将来的に失敗時リトライや DLQ 書き込みなどをここに実装します。
    """

    def __init__(self, region: str):
        from sending_dapps.region_registry import get_region_config
        cfg = get_region_config(region)
        try:
            from network.sending_DAG.python_sending.city_level.city_dag_handler import CityDAGHandler
        except ImportError:
            CityDAGHandler = None
            logger.warning("CityDAGHandler が見つかりません。DAG 投げ込みは無効化されます。")

        if CityDAGHandler:
            self.handler = CityDAGHandler(batch_interval=1, dag_url=cfg["dag_url"])
        else:
            self.handler = None

    async def add_transaction(self, sender, receiver, amount, tx_type="send"):
        """
        非同期で DAG へ投げ込む。成功すると (dag_id, dag_hash) を返す。
        """
        if not self.handler:
            # モック ID/ハッシュを返す
            dummy_id = "dummy_tx_id_" + uuid.uuid4().hex[:8]
            dummy_hash = "dummy_hash_" + uuid.uuid4().hex[:16]
            return (dummy_id, dummy_hash)

        try:
            return await self.handler.add_transaction(sender, receiver, amount, tx_type=tx_type)
        except Exception as e:
            logger.exception(f"DAG 投げ込み失敗: {e}")
            # 例外時はどのように扱うか要検討（DLQ など）
            raise
