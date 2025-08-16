# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\tests\test_file_store.py
import pytest
from poh_storage.file_store import FileStore

@pytest.mark.asyncio
async def test_file_store(tmp_path):
    fs = FileStore(str(tmp_path))
    await fs.save("a", b"hello")
    assert await fs.exists("a")
    data = await fs.load("a")
    assert data == b"hello"
    keys = await fs.list_keys()
    assert "a" in keys
    await fs.remove("a")
    assert not await fs.exists("a")
