# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\parsers\toml_parser.py
# poh_config/parsers/toml_parser.py
import tomli
from pathlib import Path
from typing import Dict, Any


async def parse(path: Path) -> Dict[str, Any]:
    # 非同期でファイルを読みたい場合は aiofiles などを使うが
    # tomli は sync-only なので run_in_executor で回避
    from asyncio import get_running_loop
    loop = get_running_loop()

    def _load() -> Dict[str, Any]:
        with path.open("rb") as f:
            return tomli.load(f)
    return await loop.run_in_executor(None, _load)
