# D:\city_chain_project\DAGs\libs\algorithm\poh_ttl\poh_ttl\manager.py
import time
import asyncio
import logging
from typing import List

from poh_storage.storage import StorageManager
from .exceptions import TTLManagerError

logger = logging.getLogger(__name__)

class TTLManager:
    """
    PoH トランザクションの TTL 管理とガベージコレクション。
    StorageManager を使って保存済トランザクションをスキャンし、
    TTL 秒を過ぎたものを削除する。
    """

    def __init__(self, storage_manager: StorageManager, ttl_seconds: int):
        self.storage_manager = storage_manager
        self.ttl_seconds     = ttl_seconds
        self._task = None

    async def scan_once(self) -> List[str]:
        """
        一回だけスキャンして、期限切れトランザクションを削除し、
        削除した tx_id のリストを返す。
        """
        now = time.time()
        expired: List[str] = []
        try:
            ids = await self.storage_manager.list_txs()
            for tx_id in ids:
                meta = await self.storage_manager.sqlite_store.load(tx_id)
                if not meta:
                    continue
                storage_hash, timestamp = meta
                if now - timestamp > self.ttl_seconds:
                    await self.storage_manager.delete_tx(tx_id)
                    expired.append(tx_id)
            return expired
        except Exception as e:
            raise TTLManagerError(f"scan_once failed: {e}") from e

    def run(self, interval_seconds: int) -> None:
        """
        バックグラウンドで定期的に scan_once() を呼ぶタスクを起動する。
        """
        if self._task:
            logger.warning("TTLManager already running")
            return
        self._task = asyncio.create_task(self._loop(interval_seconds))

    async def _loop(self, interval: int) -> None:
        while True:
            expired = await self.scan_once()
            if expired:
                logger.info(f"TTL GC removed: {expired}")
            await asyncio.sleep(interval)
