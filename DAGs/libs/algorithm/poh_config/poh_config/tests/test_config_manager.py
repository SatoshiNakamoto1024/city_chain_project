# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\tests\test_config_manager.py
# poh_config/tests/test_config_manager.py
import pytest
import json
from pathlib import Path
from poh_config.config import ConfigManager
from poh_config.types import Config

@pytest.mark.asyncio
async def test_load_and_get(tmp_path):
    p = tmp_path / "conf.json"
    data = {"MIN_POH_REQUIRED": 42, "TTL_SECONDS": 1.23}
    p.write_text(json.dumps(data), encoding="utf-8")

    cfgm = ConfigManager(p)
    loaded = await cfgm.load()
    assert loaded == data
    assert cfgm.get("MIN_POH_REQUIRED") == 42

    # 同期ロード
    loaded2 = cfgm.load_sync()
    assert loaded2 == data

    # 型変換
    cfg_obj = Config.from_dict(cfgm._data)
    assert isinstance(cfg_obj, Config)
    assert cfg_obj.MIN_POH_REQUIRED == 42
    assert cfg_obj.TTL_SECONDS == 1.23
