# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\middleware.py
"""
poh_metrics.middleware
======================
aiohttp 用ミドルウェア & gRPC インターセプターで
HTTP/gRPC リクエスト数と遅延を計測します。
"""

from __future__ import annotations

import functools
import time
from typing import Awaitable, Callable

from aiohttp import web
import grpc

from .collector import observe_verify
from .metrics import get_metric
from .registry import get_registry

__all__ = ["metrics_middleware", "GrpcMetricsInterceptor", "observe_verify"]


# --------------------------------------------------------------------------- #
# aiohttp middleware
# --------------------------------------------------------------------------- #
@web.middleware
async def metrics_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
) -> web.StreamResponse:
    """
    1. 各 HTTP リクエストをカウント               … http_requests_total
    2. レイテンシを PoH verify レイテンシとして記録 … observe_verify()
       └ ラベル result は `success` (<400) / `failure` (>=400 or 例外)
    """
    start   = time.perf_counter()
    status  = 500          # デフォルト（ハンドラ走る前に落ちても 5xx とする）
    try:
        response: web.StreamResponse = await handler(request)
        status = response.status
        return response
    except web.HTTPException as exc:   # 4xx, 5xx をここで捕捉
        status = exc.status
        raise                           # ← 呼び出し側へ再送出
    finally:
        latency = time.perf_counter() - start
        result  = "success" if status < 400 else "failure"

        reg = get_registry()

        # --- request カウンタ ------------------------------------------------
        get_metric("http_requests_total", reg).labels(
            method   = request.method,
            endpoint = request.path,
            status   = str(status),
        ).inc()

        # --- レイテンシを verify 系メトリクスに流用 -------------------------
        await observe_verify(result, latency, registry=reg)


class GrpcMetricsInterceptor(grpc.aio.ServerInterceptor):
    """
    grpc.aio サーバー向けメトリクス収集インターセプター。
    """

    async def intercept_service(self, continuation, handler_call_details):
        method_name = handler_call_details.method
        handler = await continuation(handler_call_details)
        if handler is None:
            return None  # ノーオペ

        async def _wrap(behaviour):
            @functools.wraps(behaviour)
            async def wrapper(request, context):
                start = time.perf_counter()
                try:
                    return await behaviour(request, context)
                finally:
                    reg = get_registry()
                    code = context.code().name if context.code() else "UNKNOWN"
                    get_metric("grpc_requests_total", reg).labels(
                        method=method_name,
                        code=code,
                    ).inc()
                    await observe_verify("grpc", time.perf_counter() - start)

            return wrapper

        if handler.unary_unary:
            return grpc.unary_unary_rpc_method_handler(
                await _wrap(handler.unary_unary),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        # 他 RPC タイプは必要に応じ実装
        return handler
