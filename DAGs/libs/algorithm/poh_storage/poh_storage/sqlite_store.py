# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\sqlite_store.py
import aiosqlite
from typing import Optional


class SQLiteStore:
    """
    Async SQLite-based storage for Tx metadata (hash, timestamp).
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def init(self):
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS txs (
                tx_id TEXT PRIMARY KEY,
                storage_hash TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
            """
        )
        await self._conn.commit()

    async def save(self, tx_id: str, storage_hash: str, timestamp: float):
        await self._conn.execute(
            "INSERT OR REPLACE INTO txs (tx_id, storage_hash, timestamp) VALUES (?, ?, ?)",
            (tx_id, storage_hash, timestamp)
        )
        await self._conn.commit()

    async def load(self, tx_id: str) -> Optional[tuple[str, float]]:
        cursor = await self._conn.execute(
            "SELECT storage_hash, timestamp FROM txs WHERE tx_id = ?", (tx_id,)
        )
        row = await cursor.fetchone()
        return row if row else None

    async def remove(self, tx_id: str) -> None:
        await self._conn.execute("DELETE FROM txs WHERE tx_id = ?", (tx_id,))
        await self._conn.commit()

    async def list_ids(self) -> list[str]:
        cursor = await self._conn.execute("SELECT tx_id FROM txs")
        return [row[0] for row in await cursor.fetchall()]
