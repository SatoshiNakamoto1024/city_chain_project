# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\exporter\prometheus.py
# -*- coding: utf-8 -*-
"""
Prometheus Exporter

* `/metrics` HTTP サーバをバックグラウンドで立てて Gauge を更新
"""

from __future__ import annotations

import logging
import threading
import time
from typing import List, Tuple

from prometheus_client import Gauge, start_http_server

from ..config import settings
from ..tracker import AsyncTracker

_logger = logging.getLogger(__name__)


def _update_gauge(gauge: Gauge, stats: List[Tuple[str, float]]) -> None:
    """
    Gauge ラベルを最新状態に置き換える。
    """
    # 既存ラベルを全削除 → 追加（数が少ない前提）
    gauge.clear()
    for holder_id, score in stats:
        gauge.labels(holder_id=holder_id).set(score)


def start_prometheus_exporter(tracker: AsyncTracker) -> None:
    """
    バックグラウンド Thread で定期収集 → /metrics へ露出。
    """
    port = settings.prometheus_port or 8001
    # FastAPI とポート被りを避けるため別ポートにするのが無難
    start_http_server(port)
    g = Gauge("hold_weighted_score", "Weighted PoH holding score", ["holder_id"])
    _logger.info("Prometheus exporter started at :%d/metrics", port)

    def _loop() -> None:
        while True:
            stats = tracker.snapshot()  # List[(holder, score)]
            _update_gauge(g, stats)
            time.sleep(settings.collect_interval)

    thread = threading.Thread(target=_loop, name="prom-exporter", daemon=True)
    thread.start()
