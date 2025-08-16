# network/tests/conftest.py
"""共通 pytest fixture 群."""

from __future__ import annotations
import os, sys
import asyncio
import pytest
from pathlib import Path
from typing import AsyncIterator, Iterator

ROOT = Path(__file__).resolve().parents[2]  # city_chain_project/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
    
# ─────────────────────────────────────────
# event-loop (asyncio モードの調整)
# ─────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:  # pytest-asyncio 用
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# ─────────────────────────────────────────
# MongoDB 接続情報
# ─────────────────────────────────────────
@pytest.fixture(scope="session")
def mongo_uri() -> str:
    """
    - CI / 実機 … 環境変数 MONGODB_URI をそのまま返す  
    - 無ければ mongomock を指すダミー URI を返す
    """
    return os.getenv("MONGODB_URI", "mongomock://localhost")

@pytest.fixture(scope="session")
def mongo_dbname() -> str:
    return os.getenv("DB_NAME", "unit_test_db")
