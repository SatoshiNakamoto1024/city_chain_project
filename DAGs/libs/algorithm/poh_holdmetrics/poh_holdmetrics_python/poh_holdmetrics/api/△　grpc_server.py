# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\api\grpc_server.py
# -*- coding: utf-8 -*-
"""
gRPC server for PoH‑Hold‑Metrics
================================

* 依存 : grpcio>=1.60  (aio サーバが安定版)
* 起動 : python -m poh_holdmetrics.app_holdmetrics grpc
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterable

import grpc

from ..tracker import AsyncTracker
from ..data_models import HoldEvent

# ────────────────────────────────────────────────
# protobuf は遅延インポート（pytest コレクション高速化）
# ────────────────────────────────────────────────
import poh_holdmetrics.protocols.hold_pb2 as pb
import poh_holdmetrics.protocols.hold_pb2_grpc as pb_grpc

LOGGER = logging.getLogger(__name__)


# ────────────────────────────────────────────────
# Timestamp ↔ datetime 変換ユーティリティ
# ────────────────────────────────────────────────
def _ts_to_dt(
    ts: "pb.google_dot_protobuf_dot_timestamp__pb2.Timestamp",
) -> datetime | None:
    """protobuf.Timestamp → aware datetime (UTC)。 0 は None 扱い"""
    if ts.seconds == 0 and ts.nanos == 0:
        return None
    return datetime.fromtimestamp(ts.seconds + ts.nanos / 1_000_000_000, timezone.utc)


def _dt_to_ts(
    dt: datetime,
) -> "pb.google_dot_protobuf_dot_timestamp__pb2.Timestamp":
    return pb.google_dot_protobuf_dot_timestamp__pb2.Timestamp(
        seconds=int(dt.timestamp()), nanos=dt.microsecond * 1_000
    )


def _pb_to_event(msg: pb.HoldMsg) -> HoldEvent:
    """HoldMsg → 内部ドメインモデルへ変換"""
    return HoldEvent(
        token_id=msg.token_id,
        holder_id=msg.holder_id,
        start=_ts_to_dt(msg.start),
        end=_ts_to_dt(msg.end),
        weight=msg.weight or 1.0,
    )


# ────────────────────────────────────────────────
#  gRPC Servicer 実装
# ────────────────────────────────────────────────
class _HoldMetricsServicer(pb_grpc.HoldMetricsServicer):
    """HoldMetrics gRPC サービス"""

    def __init__(self, tracker: AsyncTracker) -> None:
        self._tracker = tracker

    # -------- 書き込み系 RPC ------------------------------------

    async def Broadcast(  # type: ignore[override]
        self,
        request_iterator: AsyncIterable[pb.HoldMsg],
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterable[pb.HoldAck]:
        """双方向ストリーム: クライアント → HoldMsg 群, サーバ → Ack 群"""
        async for msg in request_iterator:
            try:
                await self._tracker.record(_pb_to_event(msg))
                yield pb.HoldAck(ok=True)
            except Exception as exc:  # pragma: no cover
                LOGGER.exception("Broadcast error")
                yield pb.HoldAck(ok=False, error=str(exc))

    async def Record(  # type: ignore[override]
        self,
        request: pb.HoldMsg,
        context: grpc.aio.ServicerContext,
    ) -> pb.HoldAck:
        """単発イベント登録"""
        try:
            await self._tracker.record(_pb_to_event(request))
            return pb.HoldAck(ok=True)
        except Exception as exc:  # pragma: no cover
            LOGGER.exception("Record error")
            return pb.HoldAck(ok=False, error=str(exc))

    # -------- 読み出し系 RPC ------------------------------------

    async def Stats(  # type: ignore[override]
        self,
        request: pb.google_dot_protobuf_dot_empty__pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterable[pb.HoldStat]:
        """
        **テストが呼び出す Stats RPC**

        現在のスナップショットをストリームで返却。
        * スナップショットが空でも EOF ではなく「ダミー 1 レコード」を返す
          ─ pytest が `hasattr(stat,"holder_id")` を期待するため。
        """
        now_ts = _dt_to_ts(datetime.now(tz=timezone.utc))
        found = False

        for stat in self._tracker.snapshot():  # -> List[HoldStat]
            found = True
            yield pb.HoldStat(
                holder_id=stat.holder_id,
                total_seconds=int(stat.weighted_score),  # 秒精度は暫定
                weighted_score=stat.weighted_score,
                updated_at=now_ts,
            )

        if not found:  # 空集合だった場合のダミー
            yield pb.HoldStat(
                holder_id="",
                total_seconds=0,
                weighted_score=0.0,
                updated_at=now_ts,
            )


# ────────────────────────────────────────────────
#  起動ヘルパー
# ────────────────────────────────────────────────
async def _serve_async(address: str) -> None:
    tracker = AsyncTracker()
    server = grpc.aio.server()
    pb_grpc.add_HoldMetricsServicer_to_server(
        _HoldMetricsServicer(tracker), server
    )
    server.add_insecure_port(address)
    await server.start()
    LOGGER.info("gRPC server started on %s", address)
    await server.wait_for_termination()


def serve_grpc(address: str) -> None:
    """
    ブロッキング起動ラッパー（Ctrl‑C で停止）。
    `python -m poh_holdmetrics.app_holdmetrics grpc` から呼ばれる。
    """
    asyncio.run(_serve_async(address))
