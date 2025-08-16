# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\recovery.py
import logging
import asyncio
from .storage import StorageManager

logger = logging.getLogger(__name__)


async def perform_recovery(base_path: str, sqlite_path: str) -> None:
    manager = await StorageManager.create(base_path, sqlite_path)
    try:
        valid = await manager.recover()
        logger.info(f"Recovery complete: {len(valid)} valid transactions")
    finally:
        await manager.close()
