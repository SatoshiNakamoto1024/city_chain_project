# D:\city_chain_project\network\DAGs\common\observability\__init__.py
"""
common.observability  ―  パッケージ公開 API
"""
from .tracing import init_tracer_provider
from .metrics import init_metrics
from .exporters import init_exporters


def init_observability(service_name: str) -> None:
    """Tracing・Metrics をまとめて初期化"""
    init_tracer_provider(service_name)
    init_metrics()
    init_exporters(service_name)


__all__ = ["init_observability"]
