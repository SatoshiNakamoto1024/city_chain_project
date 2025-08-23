# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\file_store.py
import aiofiles
from pathlib import Path


class FileStore:
    """
    Async file-based storage for raw Tx payloads.
    """

    def __init__(self, base_path: str):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    async def save(self, key: str, data: bytes) -> None:
        path = self.base / f"{key}.bin"
        async with aiofiles.open(path, 'wb') as f:
            await f.write(data)

    async def load(self, key: str) -> bytes:
        path = self.base / f"{key}.bin"
        async with aiofiles.open(path, 'rb') as f:
            return await f.read()

    async def exists(self, key: str) -> bool:
        return (self.base / f"{key}.bin").exists()

    async def remove(self, key: str) -> None:
        path = self.base / f"{key}.bin"
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    async def list_keys(self) -> list[str]:
        return [p.stem for p in self.base.glob('*.bin')]
