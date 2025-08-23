# \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\api\http_server.py
# -*- coding: utf-8 -*-
"""
HTTP API (FastAPI)

* POST /hold     … 単一保持イベントを非同期登録
* GET  /stats    … 最新スナップショットを返す
* GET  /healthz  … Liveness-Probe
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import FastAPI, HTTPException, status

from ..data_models import HoldEvent, HoldStat
from ..tracker import AsyncTracker

_logger = logging.getLogger(__name__)
app = FastAPI(title="PoH Hold Metrics HTTP API")
tracker = AsyncTracker()


# --------------------------------------------------------------------------- #
# End-points
# --------------------------------------------------------------------------- #
@app.post("/hold", status_code=status.HTTP_202_ACCEPTED)
async def post_hold(event: HoldEvent) -> dict[str, str]:
    """
    単一の保持イベントを非同期で記録します。
    """
    try:
        await tracker.record(event)
        return {"status": "accepted"}
    except Exception as exc:  # pragma: no cover
        # 例外は 500 に変換（詳細はログに残す）
        _logger.exception("Failed to record hold event: %s", exc)
        raise HTTPException(status_code=500, detail="failed to record") from exc


@app.get("/stats", response_model=list[HoldStat])
async def get_stats() -> List[HoldStat]:
    """
    現在の累積スコアを返却します。
    """
    # tracker.snapshot() → List[(holder_id, score)]
    return [
        HoldStat(holder_id=holder_id, weighted_score=score)
        for holder_id, score in tracker.snapshot()
    ]


@app.get("/healthz", response_model=dict[str, str])
async def healthz() -> dict[str, str]:
    """
    単純な Liveness-Probe 用エンドポイント。
    """
    return {"status": "healthy"}
