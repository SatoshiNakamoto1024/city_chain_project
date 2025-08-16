# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\tests\test_toml_parser.py
# poh_config/tests/test_toml_parser.py
import pytest
import tempfile
from pathlib import Path
from poh_config.parsers.toml_parser import parse

@pytest.mark.asyncio
async def test_toml_parser(tmp_path):
    p = tmp_path / "conf.toml"
    p.write_text("MIN_POH_REQUIRED = 7\ntime=\"2021-01-01T00:00:00Z\"\nTTL_SECONDS = 3600.5")
    d = await parse(p)
    assert d["MIN_POH_REQUIRED"] == 7
    assert float(d["TTL_SECONDS"]) == 3600.5
