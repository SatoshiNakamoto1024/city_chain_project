# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\storage.py
import asyncio
from typing import Optional
from .file_store import FileStore
from .sqlite_store import SQLiteStore
from .hash_utils import sha256_hex

class StorageManager:
    """
    High-level API for PoH Tx persistence and recovery.
    """

    def __init__(
        self,
        file_store: FileStore,
        sqlite_store: SQLiteStore,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        self.file_store = file_store
        self.sqlite_store = sqlite_store
        self.loop = loop or asyncio.get_event_loop()

    @classmethod
    async def create(
        cls,
        base_path: str,
        sqlite_path: str,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> 'StorageManager':
        fs = FileStore(base_path)
        ss = SQLiteStore(sqlite_path)
        await ss.init()
        return cls(fs, ss, loop)

    async def save_tx(self, tx) -> None:
        data = tx.payload
        hash_hex = sha256_hex(data)
        await self.file_store.save(tx.tx_id, data)
        await self.sqlite_store.save(tx.tx_id, hash_hex, tx.timestamp)

    async def load_tx(self, tx_id: str):
        meta = await self.sqlite_store.load(tx_id)
        if not meta:
            return None
        hash_hex, timestamp = meta
        data = await self.file_store.load(tx_id)
        if sha256_hex(data) != hash_hex:
            raise ValueError(f"Hash mismatch for tx_id={tx_id}")
        from poh_storage.types import Tx
        # Tx の定義に payload フィールドがある想定なので、data を渡す
        return Tx(
            tx_id=tx_id,
            holder_id="",        # 必要なら保存時に holder_id も永続化する
            timestamp=timestamp,
            payload=data,        # ここを追加
        )

    async def delete_tx(self, tx_id: str) -> None:
        await self.file_store.remove(tx_id)
        await self.sqlite_store.remove(tx_id)

    async def list_txs(self) -> list[str]:
        return await self.sqlite_store.list_ids()

    async def recover(self) -> list[str]:
        valid = []
        for tx_id in await self.list_txs():
            try:
                await self.load_tx(tx_id)
                valid.append(tx_id)
            except Exception:
                await self.delete_tx(tx_id)
        return valid

    async def close(self):
        """
        Close the underlying SQLite connection and shut down the default executor.
        """
        # 1) Close aiosqlite connection
        conn = getattr(self.sqlite_store, "_conn", None)
        if conn:
            await conn.close()
        # 2) Shutdown default ThreadPoolExecutor so no threads remain
        loop = asyncio.get_running_loop()
        await loop.shutdown_default_executor()
