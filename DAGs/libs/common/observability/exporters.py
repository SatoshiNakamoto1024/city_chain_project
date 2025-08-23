# D:\city_chain_project\network\DAGs\common\observability\exporters.py
"""
observability.exporters
-----------------------
* OTLP gRPC Exporter  … tracing.py 内で登録済み
* Prometheus client  … metrics.py 内で start_http_server
ここでは「MongoDB コレクタ」だけ実装
"""
from __future__ import annotations
import time
from pymongo import monitoring
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from observability.metrics import LATENCY_HIST


class _CommandLogger(monitoring.CommandListener):
    """insert / update のレイテンシを Histogram で記録"""

    def __init__(self):
        self._starts: dict[int, float] = {}

    def started(self, event):
        if event.command_name in ("insert", "update"):
            self._starts[event.request_id] = time.time()

    def succeeded(self, event):
        t0 = self._starts.pop(event.request_id, None)
        if t0 is not None:
            LATENCY_HIST.observe(time.time() - t0)

    def failed(self, event):
        self._starts.pop(event.request_id, None)


def init_exporters(service_name: str):
    """Mongo コレクタを登録"""
    monitoring.register(_CommandLogger())
