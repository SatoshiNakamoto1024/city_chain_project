# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\batcher.py
# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\batcher.py
"""
Async batch-compression for PoH-ACK objects.

* 収集対象 : `poh_ack.models.AckRequest`
* 圧縮方式 : gzip（デフォルト）／zstd（`zstandard` が import 可能なら自動採用）
* 出力型   : `PackedBatch`（header + payload）の Pydantic モデル

Public API
==========

* **AsyncBatcher** – 非同期で ACK を集め、件数／タイムアウトで自動 flush
* **Batcher**      – `AsyncBatcher` の後方互換エイリアス
* **pack_acks** / **unpack_batch** – list[AckRequest] ↔ PackedBatch 相互変換
"""

from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable, Iterable, Optional

from poh_ack.models import AckRequest

from .compression import compress, decompress
from .types import BatchHeader, PackedBatch

_JSON_SEP = (",", ":")  # ホワイトスペースを省いてサイズ最小化


# ────────────────────────────
# (de)serialization helpers
# ────────────────────────────
def _json_dump(objs: Iterable[AckRequest]) -> bytes:
    """Ack の list → UTF-8 JSON (minified)"""
    return json.dumps([o.model_dump() for o in objs],
                      separators=_JSON_SEP).encode("utf-8")


def pack_acks(acks: list[AckRequest]) -> PackedBatch:
    """
    AckRequest list → 圧縮済みバッチ

    Returns
    -------
    PackedBatch
        .header.count        : 件数
        .header.compression  : "gzip" / "zstd"
        .payload             : 圧縮バイト列
    """
    raw = _json_dump(acks)
    codec, payload = compress(raw)
    header = BatchHeader(count=len(acks), compression=codec)
    return PackedBatch(header=header, payload=payload)


def unpack_batch(batch: PackedBatch) -> list[AckRequest]:
    """PackedBatch → AckRequest list"""
    raw = decompress(batch.header.compression, batch.payload)
    objs = json.loads(raw)
    return [AckRequest.model_validate(o) for o in objs]


# ────────────────────────────
# Async batcher implementation
# ────────────────────────────
class AsyncBatcher:
    """
    非同期 ACK バッチャ

    Parameters
    ----------
    max_items :
        1 バッチ当たりの最大 ACK 件数（超えたら即 flush）
    timeout :
        先頭 ACK を受信してから flush するまでの秒数
    sink :
        ``async def sink(batch: PackedBatch)``
        – flush 時に呼ばれるコールバック
    loop :
        明示しない場合 ``asyncio.get_event_loop()`` を使用
    """

    def __init__(
        self,
        *,
        max_items: int = 256,
        timeout: float = 0.5,
        sink: Callable[[PackedBatch], Awaitable[None]],
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        if max_items <= 0:
            raise ValueError("max_items must be > 0")
        if timeout <= 0:
            raise ValueError("timeout must be > 0")

        self.max_items = max_items
        self.timeout = timeout
        self.sink = sink
        self.loop = loop or asyncio.get_event_loop()

        self._queue: asyncio.Queue[AckRequest] = asyncio.Queue()
        self._task: Optional[asyncio.Task[None]] = None
        self._closing = asyncio.Event()

    # ───────────── lifecycle ─────────────

    async def start(self) -> None:
        """バックグラウンドタスクを開始"""
        if self._task is not None:
            raise RuntimeError("AsyncBatcher already running")
        self._closing.clear()
        self._task = self.loop.create_task(self._worker())

    async def stop(self) -> None:
        """キューをドレインし flush してタスク終了"""
        if self._task is None:
            return
        self._closing.set()
        await self._task
        self._task = None

    async def enqueue(self, ack: AckRequest) -> None:
        """ACK を投入（back-pressure あり）"""
        await self._queue.put(ack)

    # ───────────── internal ──────────────

    async def _worker(self) -> None:
        buf: list[AckRequest] = []
        first_ts = self.loop.time()

        while True:
            # ― ❶ shutdown 条件 ―
            if self._closing.is_set() and self._queue.empty() and not buf:
                break

            # ― ❷ queue get (with timeout) ―
            remain = self.timeout - (self.loop.time() - first_ts)
            try:
                ack = await asyncio.wait_for(
                    self._queue.get(), timeout=max(0.0, remain)
                )
                buf.append(ack)
            except asyncio.TimeoutError:
                # read 無しでタイムアウト → flush 判定へ
                pass

            # ― ❸ flush 判定 ―
            time_up = self.loop.time() - first_ts >= self.timeout
            full = len(buf) >= self.max_items
            shutdown = self._closing.is_set()

            if buf and (full or time_up or shutdown):
                await self._flush(buf)
                buf.clear()
                first_ts = self.loop.time()

    async def _flush(self, buf: list[AckRequest]) -> None:
        """バッファを PackedBatch にして sink へ"""
        batch = pack_acks(buf)
        await self.sink(batch)


# 旧 API 名との互換維持
Batcher = AsyncBatcher

__all__ = [
    "AsyncBatcher",
    "Batcher",
    "pack_acks",
    "unpack_batch",
]
