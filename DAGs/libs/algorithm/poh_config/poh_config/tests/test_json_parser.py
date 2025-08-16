# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\tests\test_json_parser.py
# poh_config/tests/test_json_parser.py
import pytest
import json
from pathlib import Path
from poh_config.parsers.json_parser import parse

@pytest.mark.asyncio
async def test_json_parser(tmp_path):
    p = tmp_path / "conf.json"
    obj = {"MIN_POH_REQUIRED": 3, "TTL_SECONDS": 123.4}
    p.write_text(json.dumps(obj), encoding="utf-8")
    d = await parse(p)
    assert d == obj
