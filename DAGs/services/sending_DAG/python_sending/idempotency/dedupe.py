import aioredis
from .errors import IdempotencyError


class IdempotencyStore:
    """
    Redisを使って「処理済みTxIDの集合」を管理。
    """
    def __init__(self, redis_url: str = "redis://localhost"):
        self.redis_url = redis_url
        self.redis = None

    async def init(self):
        self.redis = await aioredis.from_url(self.redis_url)

    async def already_processed(self, tx_id: str) -> bool:
        return await self.redis.sismember("processed_tx", tx_id)

    async def mark_processed(self, tx_id: str):
        await self.redis.sadd("processed_tx", tx_id)


async def ensure_not_duplicate(tx_id: str, store: IdempotencyStore):
    """
    重複チェック → 処理済みであれば例外、そうでなければマーク
    """
    if await store.already_processed(tx_id):
        raise IdempotencyError(f"Tx {tx_id} は既に処理済みです。")
    await store.mark_processed(tx_id)
