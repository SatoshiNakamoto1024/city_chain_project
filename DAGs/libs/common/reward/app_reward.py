# D:\city_chain_project\network\DAGs\common\reward\app_reward.py
"""
app_reward.py
=============
PoH ACK を受け取り、RewardSystem へスコアを記録する FastAPI サービス。

起動例:
    python -m network.DAGs.reward.app_reward
"""
from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel, Field
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# ────────────────────────────────────────────────
# 内部モジュールの絶対 import
# ────────────────────────────────────────────────
from reward.schemas import PoH
from reward.reward_system import (
    _reward_sys as reward_sys,
    on_poh_ack_confirmed,
)

app = FastAPI(title="Reward Service")


# ────────────────────────────────────────────────
# 入力スキーマ（Pydantic）
# ────────────────────────────────────────────────
class PoHIn(BaseModel):
    holder_id: str
    original_tx_id: str
    lat: float
    lon: float
    ttl_sec: int = Field(ge=0)

    tx_holder_lat: float
    tx_holder_lon: float
    online_rate: float = 1.0


# ────────────────────────────────────────────────
# エンドポイント
# ────────────────────────────────────────────────
@app.post("/poh_ack")
async def poh_ack(poh_in: PoHIn):
    """
    PoH が “accepted” になった瞬間に呼び出される想定。
    - コア情報のみで PoH dataclass を生成
    - 追加パラメータは個別引数で渡す
    """
    poh_core = {
        "holder_id": poh_in.holder_id,
        "original_tx_id": poh_in.original_tx_id,
        "lat": poh_in.lat,
        "lon": poh_in.lon,
        "ttl_sec": poh_in.ttl_sec,
    }
    poh = PoH(**poh_core)

    on_poh_ack_confirmed(
        poh,
        tx_holder_lat=poh_in.tx_holder_lat,
        tx_holder_lon=poh_in.tx_holder_lon,
        online_rate=poh_in.online_rate,
    )
    return {"status": "recorded"}


@app.get("/score/{node_id}")
async def score(node_id: str):
    """指定ノードの累積スコア"""
    return {"score": reward_sys.get_score(node_id)}


@app.get("/scores")
async def scores():
    """全ノードのスコアマップ"""
    return reward_sys.all_scores()


# ────────────────────────────────────────────────
# スクリプト起動
# ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "network.DAGs.reward.app_reward:app",
        host="0.0.0.0",
        port=8082,
        log_level="info",
    )
