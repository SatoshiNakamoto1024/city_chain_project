# D:\city_chain_project\network\DAGs\common\grpc_dag\server\interceptors.py
"""
gRPC Server-side interceptors
─────────────────────────────
1. LoggingInterceptor     : すべてのリクエスト／レスポンスを INFO レベルで記録
2. AuthInterceptor        : mTLS や MAC-token を強制し、失敗時は UNAUTHENTICATED
3. ExceptionInterceptor   : 業務例外を INTERNAL にマッピングしトレースを隠蔽
4. MetricsInterceptor     : Prometheus 用メトリクスを集計
"""

from __future__ import annotations

import logging
import time
import traceback
from typing import Callable, Any

import grpc
from grpc import StatusCode, ServerInterceptor

# ──────────────────────────
# ロガー
# ──────────────────────────
logger = logging.getLogger("grpc_dag.server")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s  %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ──────────────────────────
# 1. LoggingInterceptor
# ──────────────────────────
class LoggingInterceptor(ServerInterceptor):
    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        handler = continuation(handler_call_details)
        method = handler_call_details.method

        def wrapper(request, context):
            start = time.time()
            logger.info("▶ %s  → %s", context.peer(), method)
            resp = handler.unary_unary(request, context)
            logger.info("◀ %s  ← %s [%.2f ms]", context.peer(), method, (time.time() - start) * 1000)
            return resp

        return grpc.unary_unary_rpc_method_handler(
            wrapper,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

# ──────────────────────────
# 2. AuthInterceptor
#    * mTLS の Subject または Metadata に載る `mac-token`
# ──────────────────────────
class AuthInterceptor(ServerInterceptor):
    def __init__(self, valid_tokens: set[str]):
        self.valid_tokens = valid_tokens

    def intercept_service(self, continuation, call):
        handler = continuation(call)

        def auth_wrapper(request, context):
            # ① mTLS DN でチェック（例：/CN=node-123 など）
            ssl_ctx = context.auth_context()
            dn = ssl_ctx.get("x509_common_name", [b""])[0].decode()
            if dn.startswith("node-"):  # 証明書 CN が 'node-xxx'
                return handler.unary_unary(request, context)

            # ② Metadata-token
            token = ""
            for key, value in context.invocation_metadata():
                if key == "mac-token":
                    token = value
                    break

            if token not in self.valid_tokens:
                context.abort(StatusCode.UNAUTHENTICATED, "Invalid token / certificate")
            return handler.unary_unary(request, context)

        return grpc.unary_unary_rpc_method_handler(
            auth_wrapper,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

# ──────────────────────────
# 3. ExceptionInterceptor
# ──────────────────────────
class ExceptionInterceptor(ServerInterceptor):
    def intercept_service(self, continuation, call):
        handler = continuation(call)

        def safe_wrapper(request, context):
            try:
                return handler.unary_unary(request, context)
            except grpc.RpcError:  # すでに gRPC Code 済み
                raise
            except Exception as e:
                # Log full traceback but not leak to client
                logger.error("Unhandled error: %s\n%s", e, traceback.format_exc())
                context.abort(StatusCode.INTERNAL, "Internal server error")

        return grpc.unary_unary_rpc_method_handler(
            safe_wrapper,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

# ──────────────────────────
# 4. MetricsInterceptor  (簡易実装)
# ──────────────────────────
try:
    from prometheus_client import Counter, Histogram

    _REQ_COUNT = Counter(
        "grpc_requests_total",
        "gRPC request count",
        ["method", "code"],
    )
    _REQ_LAT = Histogram(
        "grpc_request_duration_seconds",
        "gRPC method latency",
        ["method"],
        buckets=(.001, .005, .01, .05, .1, .25, .5, 1, 2, 5),
    )

    class MetricsInterceptor(ServerInterceptor):
        def intercept_service(self, continuation, call):
            handler = continuation(call)
            method = call.method

            def metrics_wrapper(request, context):
                with _REQ_LAT.labels(method=method).time():
                    try:
                        resp = handler.unary_unary(request, context)
                        _REQ_COUNT.labels(method=method, code="OK").inc()
                        return resp
                    except grpc.RpcError as e:
                        _REQ_COUNT.labels(method=method, code=e.code().name).inc()
                        raise
                    except Exception:
                        _REQ_COUNT.labels(method=method, code="INTERNAL").inc()
                        raise

            return grpc.unary_unary_rpc_method_handler(
                metrics_wrapper,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

except ImportError:
    # Prometheus なしでも動く
    class MetricsInterceptor(ServerInterceptor):  # type: ignore
        def intercept_service(self, continuation, call):
            return continuation(call)

# ──────────────────────────
# helper: 全部をまとめて返す
# ──────────────────────────
def build_interceptors(valid_tokens: set[str] | None = None) -> list[ServerInterceptor]:
    """
    gRPC server 作成時::

        server = grpc.server(...)
        for itc in build_interceptors({"secret-abc"}):
            server.intercept_service(itc)

    """
    interceptors: list[ServerInterceptor] = [
        LoggingInterceptor(),
        ExceptionInterceptor(),
        MetricsInterceptor(),
    ]
    if valid_tokens is not None:
        interceptors.insert(1, AuthInterceptor(valid_tokens))  # Logging の後に認証
    return interceptors
