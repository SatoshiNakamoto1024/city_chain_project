# D:\city_chain_project\network\DAGs\common\observability\middleware.py
"""
observability.middleware
------------------------
* FastAPI 用 ASGI ミドルウェア (トレース＋メトリクス)
* gRPC 用 interceptors も (optional)
"""
from __future__ import annotations
import time
import typing as _t

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from observability.metrics import REQUEST_COUNTER
from observability.tracing import get_tracer


# ─────────────────────────────
# FastAPI / ASGI Middleware
# ─────────────────────────────
class ObservabilityMiddleware(BaseHTTPMiddleware):
    """FastAPI に組み込む::

        app.add_middleware(OpenTelemetryMiddleware)
        app.add_middleware(ObservabilityMiddleware)
    """

    async def dispatch(self, request: Request, call_next: _t.Callable[[Request], _t.Awaitable[Response]]):
        tracer = get_tracer("fastapi")
        path = request.url.path
        with tracer.start_as_current_span(path):
            t0 = time.time()
            resp = await call_next(request)
            elapsed = time.time() - t0
            status = str(resp.status_code)
            REQUEST_COUNTER.labels(endpoint=path, status=status).inc()
            return resp


# ─────────────────────────────
# gRPC Interceptor (optional)
# ─────────────────────────────
import grpc
from prometheus_client import Summary

_GRPC_LAT = Summary(
    "grpc_method_latency_seconds",
    "gRPC method latency",
    ["method", "code"],
)


class GRPCObservabilityInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method
        tracer = get_tracer("grpc")
        handler = continuation(handler_call_details)

        async def obs_wrap(request, context):
            with tracer.start_as_current_span(method):
                t0 = time.time()
                try:
                    resp = await handler.unary_unary(request, context)
                    code = context.code() or grpc.StatusCode.OK
                    return resp
                finally:
                    _GRPC_LAT.labels(method=method, code=code.name).observe(time.time() - t0)

        return grpc.unary_unary_rpc_method_handler(
            obs_wrap,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
