# city_chain_project\network\DAGs\common\transport\app_transport.py
"""
app_transport.py  ─ Transport デモ API
(変更点)
  * FastAPI(title=…, lifespan=lifespan) で gRPC サーバーを起動
  * deprecated `@app.on_event` を削除
"""
from __future__ import annotations
import contextlib
from fastapi import FastAPI, HTTPException, Query
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from transport.grpc_transport import GRPCServer, GRPCClient
from transport.retry_policy import retry

# gRPC 用: Echo Stub / Servicer
from grpc_dag.gen.dag_pb2 import TxRequest, TxResponse
from grpc_dag.gen.dag_pb2_grpc import (
    DAGServiceStub,
    DAGServiceServicer,
    add_DAGServiceServicer_to_server,
)

# ──────────────────────────────────────────
# Lifespan: gRPC サーバを起動 / 終了
# ──────────────────────────────────────────
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    class EchoServicer(DAGServiceServicer):
        def SubmitTransaction(self, request: TxRequest, context):  # type: ignore[override]
            return TxResponse(status="ECHO", message=request.payload)

    grpc_srv = GRPCServer(
        servicer=EchoServicer(),
        add_servicer_fn=add_DAGServiceServicer_to_server,
        port=0,  # 自動選択
    )
    grpc_srv.start()
    app.state.grpc_port = grpc_srv.port        # ← テスト側が参照
    try:
        yield
    finally:
        grpc_srv.stop(0)


app = FastAPI(title="Transport Demo", lifespan=lifespan)

# ──────────────────────────────────────────
# HTTP → gRPC Echo Bridge
# ──────────────────────────────────────────
@app.get("/grpc_echo")
async def grpc_echo(payload: str = Query(...)):
    port: int = app.state.grpc_port
    cli = GRPCClient(DAGServiceStub, f"localhost:{port}")
    try:
        resp: TxResponse = cli.stub.SubmitTransaction(
            TxRequest(tx_id="demo", payload=payload), timeout=1.0
        )
        return {"echo": resp.message}
    finally:
        cli.close()


# ──────────────────────────────────────────
# retry デモ
# ──────────────────────────────────────────
_fail = 0


@retry(
    max_attempts=3,
    initial_backoff=0.01,
)
def _sometimes_fail(n: int) -> str:
    global _fail
    if _fail < n:
        _fail += 1
        raise RuntimeError(f"forced fail {_fail}")
    return "ok"


@app.get("/retry_test")
async def retry_test(failures: int = Query(..., ge=0)):
    global _fail
    _fail = 0
    try:
        return {"result": _sometimes_fail(failures)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ──────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8085,
        log_level="info",
    )
