# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\tests\test_yaml_parser.py
# poh_config/tests/test_yaml_parser.py
import pytest
import yaml
from pathlib import Path
from poh_config.parsers.yaml_parser import parse

@pytest.mark.asyncio
async def test_yaml_parser(tmp_path):
    p = tmp_path / "conf.yaml"
    obj = {"MIN_POH_REQUIRED": 5, "TTL_SECONDS": 99.9}
    p.write_text(yaml.safe_dump(obj), encoding="utf-8")
    d = await parse(p)
    assert d["MIN_POH_REQUIRED"] == 5
    assert d["TTL_SECONDS"] == 99.9
