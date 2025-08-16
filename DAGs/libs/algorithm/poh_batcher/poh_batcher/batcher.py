# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\batcher.py
# poh_batcher/poh_batcher/batcher.py
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable, Iterable, Optional

from poh_ack.models import AckRequest
from .compression import compress, decompress
from .types import BatchHeader, PackedBatch, AckItem
from .storage import storage_from_url

_JSON_SEP = (",", ":")


def _json_dump(objs: Iterable[AckRequest]) -> bytes:
    return json.dumps([o.model_dump() for o in objs],
                      separators=_JSON_SEP).encode("utf-8")


def pack_acks(acks: list[AckRequest]) -> PackedBatch:
    raw = _json_dump(acks)
    codec, payload = compress(raw)
    header = BatchHeader(count=len(acks), compression=codec)
    return PackedBatch(header=header, payload=payload)


def unpack_batch(batch: PackedBatch) -> list[AckRequest]:
    raw = decompress(batch.header.compression, batch.payload)
    arr = json.loads(raw)
    return [AckRequest.model_validate(o) for o in arr]


class AsyncBatcher:
    """
    ※ 変更なし ※
    非同期 ACK 集約ロジック。外部から sink(batch) を受け取る。
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

    async def start(self) -> None:
        if self._task is not None:
            raise RuntimeError("AsyncBatcher already running")
        self._closing.clear()
        self._task = self.loop.create_task(self._worker())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._closing.set()
        await self._task
        self._task = None

    async def enqueue(self, ack: AckRequest) -> None:
        await self._queue.put(ack)

    async def _worker(self) -> None:
        buf: list[AckRequest] = []
        first_ts = self.loop.time()

        while True:
            if self._closing.is_set() and self._queue.empty() and not buf:
                break

            remain = self.timeout - (self.loop.time() - first_ts)
            try:
                ack = await asyncio.wait_for(
                    self._queue.get(), timeout=max(0.0, remain)
                )
                buf.append(ack)
            except asyncio.TimeoutError:
                pass

            time_up = (self.loop.time() - first_ts) >= self.timeout
            full = len(buf) >= self.max_items
            shutdown = self._closing.is_set()

            if buf and (full or time_up or shutdown):
                await self._flush(buf)
                buf.clear()
                first_ts = self.loop.time()

    async def _flush(self, buf: list[AckRequest]) -> None:
        batch = pack_acks(buf)
        await self.sink(batch)


class Batcher:
    """
    高レベルバッチャ：AckItem -> AckRequest 変換 + Local/S3 保存
    """

    def __init__(
        self,
        *,
        batch_size: int,
        batch_timeout: float,
        output_dir: str,
    ) -> None:
        self._storage = storage_from_url(output_dir)
        self._seq = 0
        # AsyncBatcher に sink として _save_batch を渡す
        self._inner = AsyncBatcher(
            max_items=batch_size,
            timeout=batch_timeout,
            sink=self._save_batch,
        )

    async def start(self) -> None:
        await self._inner.start()

    async def submit(self, item: AckItem) -> None:
        # AckItem -> AckRequest に変換
        req = AckRequest(
            id=item.id,
            timestamp=item.timestamp,
            signature=item.signature,
            pubkey=item.pubkey,
        )
        await self._inner.enqueue(req)

    async def stop(self) -> None:
        await self._inner.stop()

    async def _save_batch(self, batch: PackedBatch) -> None:
        # test_batcher 用：{"items":[...]} の JSON を uncompressed で保存
        acks = unpack_batch(batch)
        items = [o.model_dump() for o in acks]
        text = json.dumps({"items": items}, separators=(",", ":"))
        fname = f"{self._seq:04d}.json"
        self._seq += 1
        await self._storage.save_json(fname, text)


__all__ = [
    "AsyncBatcher",
    "Batcher",
    "pack_acks",
    "unpack_batch",
]
