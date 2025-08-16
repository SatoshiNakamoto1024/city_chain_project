# D:\city_chain_project\network\DAGs\common\observability\config.py
"""
observability.config  … 環境変数
"""
from __future__ import annotations
import os

OTLP_ENDPOINT: str = os.getenv("OTLP_GRPC_ENDPOINT", "localhost:4317")
PROM_BIND: str = os.getenv("PROMETHEUS_BIND", "0.0.0.0:8000")  # addr:port
SERVICE_NAMESPACE: str = os.getenv("SERVICE_NAMESPACE", "city-chain")
EXPORT_INTERVAL_SEC: int = int(os.getenv("OTLP_EXPORT_INTERVAL", 5))
