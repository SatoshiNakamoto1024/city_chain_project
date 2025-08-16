# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\exporter\otlp.py
# -*- coding: utf-8 -*-
"""
OpenTelemetry Metrics Exporter (OTLP Push)

* OTLP gRPC でメトリクスをプッシュ送信
* v1.23 以降の公式 API に合わせて MetricReader を利用
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from ..config import settings
from ..tracker import AsyncTracker

_logger = logging.getLogger(__name__)


def _build_attrs(holder_id: str) -> dict[str, str]:
    """共通属性を一か所で生成"""
    return {"holder_id": holder_id}


def start_otlp_exporter(tracker: AsyncTracker) -> None:
    """
    `tracker.snapshot()` を Gauge で OTLP Push 送信するバックグラウンド Exporter。
    呼び出すだけでメトリクス送信が始まる（停止制御は不要）。
    """
    endpoint = settings.otlp_endpoint or "localhost:4317"

    exporter = OTLPMetricExporter(
        endpoint=endpoint,
        insecure=True,  # → mTLS を使う場合は False + TLS 設定
    )
    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=int(settings.collect_interval * 1000),
    )
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter(__name__)

    # ObservableGauge callback
    def _observe() -> List[Tuple[float, dict[str, str]]]:
        return [(score, _build_attrs(holder_id)) for holder_id, score in tracker.snapshot()]

    meter.create_observable_gauge(
        name="hold_weighted_score",
        description="Weighted PoH holding score (seconds × weight)",
        callbacks=[lambda _: _observe()],
    )
    _logger.info("OTLP exporter started (push interval=%ss, endpoint=%s)",
                 settings.collect_interval, endpoint)
