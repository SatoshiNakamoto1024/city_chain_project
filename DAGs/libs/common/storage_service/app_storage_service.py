# D:\city_chain_project\network\DAGs\common\storage_service\app_storage_service.py
"""
app_storage_service.py
======================
`python -m network.DAGs.common.storage_service.app_storage_service`
で簡易 gRPC サーバを常駐起動。
"""
from __future__ import annotations
import signal
import sys
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage_service.service import start_storage_server
from storage_service.config import SERVER_PORT

# 起動
server, port = start_storage_server(port=SERVER_PORT, node_id="storage-node")
print(f"[StorageService] listening on {port}")

# Graceful-stop
def _sigterm(signo, frame):  # noqa: D401
    print("Stopping StorageService...")
    server.stop(0)
    sys.exit(0)

signal.signal(signal.SIGINT, _sigterm)
signal.signal(signal.SIGTERM, _sigterm)

# 無限ループ
try:
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    _sigterm(None, None)
