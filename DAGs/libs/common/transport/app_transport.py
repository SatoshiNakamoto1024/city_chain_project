# city_chain_project\network\DAGs\common\transport\app_transport.py
# network/DAGs/common/transport/app_transport.py
"""
Transport Demo API
==================
* /grpc_echo  : HTTP→gRPC ブリッジ (Echo)
* /retry_test : retry デコレータのデモ

起動
-----
python -m network.DAGs.common.transport.app_transport
"""
from __future__ import annotations
import contextlib
import logging
from fastapi import FastAPI, HTTPException, Query
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from grpc_dag.gen.dag_pb2 import TxRequest, TxResponse
from grpc_dag.gen.dag_pb2_grpc import (
    DAGServiceServicer,
    DAGServiceStub,
    add_DAGServiceServicer_to_server,
)

from transport.grpc_transport import GRPCServer, GRPCClient
from transport.retry_policy import retry

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────
# Lifespan → gRPC Echo サーバを起動
# ──────────────────────────────────────────
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    class EchoServicer(DAGServiceServicer):
        def SubmitTransaction(self, request: TxRequest, context):  # type: ignore[override]
            return TxResponse(status="ECHO", message=request.payload)

    grpc_srv = GRPCServer(
        servicer=EchoServicer(),
        add_servicer_fn=add_DAGServiceServicer_to_server,
        port=0,  # 自動割当
    )
    grpc_srv.start()
    app.state.grpc_port = grpc_srv.port
    logger.info("Echo-gRPC started on %s", grpc_srv.port)
    try:
        yield
    finally:
        grpc_srv.stop(0)
        logger.info("Echo-gRPC stopped")


# FastAPI アプリ本体
app = FastAPI(title="Transport Demo", lifespan=lifespan)
# ← httpx 0.28+ の“auto”判定でも起動するよう fallback
app.router.lifespan_context = lifespan


# ──────────────────────────────────────────
# 1. /grpc_echo  : HTTP→gRPC ブリッジ
# ──────────────────────────────────────────
@app.get("/grpc_echo")
async def grpc_echo(payload: str = Query(...)):
    port: int = app.state.grpc_port  # type: ignore[attr-defined]
    cli = GRPCClient(DAGServiceStub, f"localhost:{port}")
    try:
        resp: TxResponse = cli.stub.SubmitTransaction(
            TxRequest(tx_id="demo", payload=payload), timeout=1.0
        )
        return {"echo": resp.message}
    finally:
        cli.close()


# ──────────────────────────────────────────
# 2. retry デモ
# ──────────────────────────────────────────
_fail_counter = 0


@retry(
    max_attempts=3,
    initial_backoff=0.01,
    exceptions=(RuntimeError,),  # RuntimeError も再試行
)
def _sometimes_fail(times_to_fail: int) -> str:
    """`times_to_fail` 回までは必ず失敗し、以降 OK を返す"""
    global _fail_counter
    if _fail_counter < times_to_fail:
        _fail_counter += 1
        raise RuntimeError(f"forced fail {_fail_counter}")
    return "ok"


@app.get("/retry_test")
async def retry_test(failures: int = Query(..., ge=0)):
    global _fail_counter
    _fail_counter = 0
    try:
        return {"result": _sometimes_fail(failures)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ──────────────────────────────────────────
# CLI 起動
# ──────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8085,
        log_level="info",
        reload=False,
    )
