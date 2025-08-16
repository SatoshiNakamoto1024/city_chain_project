# D:\city_chain_project\network\DAGs\common\presence\app_presence.py
"""
app_presence.py
---------------
`python -m network.DAGs.common.presence.app_presence`
で Presence Service を起動する単純なラッパー。
"""
from __future__ import annotations
import uvicorn
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from presence.server import create_app
from node_list.config import PRESENCE_HTTP_PORT

if __name__ == "__main__":
    uvicorn.run(
        create_app(),
        host="0.0.0.0",
        port=PRESENCE_HTTP_PORT,
        log_level="info",
    )
