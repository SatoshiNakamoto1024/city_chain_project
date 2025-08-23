# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\parsers\yaml_parser.py
# poh_config/parsers/yaml_parser.py
import yaml
from pathlib import Path
from typing import Dict, Any


async def parse(path: Path) -> Dict[str, Any]:
    from asyncio import get_running_loop
    loop = get_running_loop()

    def _load() -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return await loop.run_in_executor(None, _load)
