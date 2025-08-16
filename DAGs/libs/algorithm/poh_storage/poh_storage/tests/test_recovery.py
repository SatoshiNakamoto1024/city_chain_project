# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\tests\test_recovery.py
import pytest
from poh_storage.recovery import perform_recovery

@pytest.mark.asyncio
async def test_perform_recovery(tmp_path, caplog):
    base = tmp_path / "d"
    db   = tmp_path / "d" / "poh.db"
    caplog.set_level("INFO")

    # perform_recovery 内で必ず manager.close() を呼ぶ実装になっていること
    await perform_recovery(str(base), str(db))
    assert "Recovery complete:" in caplog.text
