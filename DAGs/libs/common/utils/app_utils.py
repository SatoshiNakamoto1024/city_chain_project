# network/DAGs/common/utils/app_utils.py
"""
Utils Demo API
==============

* /tx_types                 : TxType 一覧
* /tx_types/validate        : TxType 妥当性チェック
* /dag/sort                 : トポロジカルソート
* /dag/detect_cycle         : サイクル検出
* /dag/flatten              : エッジ→隣接リスト変換
* /constants                : 共通定数取得
* /errors/*                 : 共通例外デモ
"""
from __future__ import annotations
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.tx_types import TxType
from utils.dag_utils import topological_sort, detect_cycle, flatten_edges
from utils.constants import (
    MAX_DAG_NODES,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_BACKOFF_SECONDS,
    SHARD_SIZE_LIMIT,
)
from utils.errors import DAGCycleError, InvalidTxTypeError

app = FastAPI(title="Utils Demo")

# ───────────────────────────────
# Pydantic モデル
# ───────────────────────────────
class EdgeList(BaseModel):
    edges: List[List[str]] = Field(
        ..., description='[["A","B"], ["B","C"], ...] の形式'
    )

# ───────────────────────────────
# TxType
# ───────────────────────────────
@app.get("/tx_types")
async def list_tx_types():
    return {"values": [t.value for t in TxType]}

@app.get("/tx_types/validate")
async def validate_tx_type(value: str):
    return {"valid": TxType.has_value(value)}

# ───────────────────────────────
# DAG ユーティリティ
# ───────────────────────────────
@app.post("/dag/sort")
async def api_topo_sort(body: EdgeList):
    graph = flatten_edges(body.edges)
    try:
        return {"order": topological_sort(graph)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/dag/detect_cycle")
async def api_detect_cycle(body: EdgeList):
    graph = flatten_edges(body.edges)
    return {"cycle": detect_cycle(graph)}

@app.post("/dag/flatten")
async def api_flatten(body: EdgeList):
    graph = flatten_edges(body.edges)
    return {"graph": graph}

# ───────────────────────────────
# Constants
# ───────────────────────────────
@app.get("/constants")
async def get_constants():
    return {
        "MAX_DAG_NODES": MAX_DAG_NODES,
        "DEFAULT_RETRY_ATTEMPTS": DEFAULT_RETRY_ATTEMPTS,
        "DEFAULT_BACKOFF_SECONDS": DEFAULT_BACKOFF_SECONDS,
        "SHARD_SIZE_LIMIT": SHARD_SIZE_LIMIT,
    }

# ───────────────────────────────
# Errors
# ───────────────────────────────
@app.get("/errors/dag_cycle")
async def raise_dag_cycle():
    raise DAGCycleError("Cycle detected")

@app.get("/errors/invalid_tx")
async def raise_invalid_tx():
    raise InvalidTxTypeError("Invalid TxType")

# ───────────────────────────────
# Exception Handlers
# ───────────────────────────────
@app.exception_handler(DAGCycleError)
async def handle_cycle_error(request: Request, exc: DAGCycleError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(InvalidTxTypeError)
async def handle_invalid_tx(request: Request, exc: InvalidTxTypeError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})
