# network/DAGs/common/observability/tracing.py
"""
observability.tracing  … OpenTelemetry TracerProvider 初期化
"""
from __future__ import annotations
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from .config import OTLP_ENDPOINT, SERVICE_NAMESPACE, EXPORT_INTERVAL_SEC

_tracer_ready = False


def init_tracer_provider(service_name: str) -> None:
    global _tracer_ready
    if _tracer_ready:  # 2 回目呼ばれても無視
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": SERVICE_NAMESPACE,
        }
    )
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    span_exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
    span_processor = BatchSpanProcessor(span_exporter,
                                        schedule_delay_millis=EXPORT_INTERVAL_SEC * 1000)
    provider.add_span_processor(span_processor)

    _tracer_ready = True


def get_tracer(pkg: str = __name__):
    return trace.get_tracer(pkg)
