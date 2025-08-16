# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tracker.py
# -*- coding: utf-8 -*-
"""
非同期保持トラッカー

* Rust 拡張 `PyAggregator` があれば高速版を使用  
* 無い場合は純 Python 実装にフォールバック
"""

from __future__ import annotations

import asyncio
import time, os
from collections import defaultdict
from typing import Dict, List, Tuple

from .data_models import HoldEvent

_DISABLE = os.environ.get("POH_DISABLE_RUST") == "1"

# ---------------------------------------------------------------------
# Rust 拡張またはフォールバック
# ---------------------------------------------------------------------
try:
    if _DISABLE:
        raise ImportError
    from poh_holdmetrics_rust import PyAggregator, PyHoldEvent  # type: ignore
    _HAS_RUST = True
except ImportError:
    _HAS_RUST = False

    class _PyAggregatorFallback:
        def __init__(self) -> None:
            self._scores: Dict[str, float] = defaultdict(float)

        async def record(self, ev):  # HoldEvent or PyHoldEvent風
            # ev.start/end が datetime か int か両対応
            if hasattr(ev.start, "timestamp"):  # datetime
                start = int(ev.start.timestamp())
                end = int(ev.end.timestamp()) if ev.end is not None else None
            else:  # int epoch
                start = int(ev.start)
                end = int(ev.end) if ev.end is not None else None

            if end is None or end <= start:
                return
            self._scores[ev.holder_id] += float(end - start) * float(ev.weight)

        def snapshot(self) -> List[Tuple[str, float]]:
            return sorted(self._scores.items())

        def gc(self) -> None:
            pass

    class PyHoldEvent:  # Rust型の代替
        def __init__(self, token_id: str, holder_id: str, start: int, end: int | None, weight: float) -> None:
            self.token_id = token_id
            self.holder_id = holder_id
            self.start = start
            self.end = end
            self.weight = weight

    PyAggregator = _PyAggregatorFallback  # type: ignore[misc]


# ---------------------------------------------------------------------
# 本体クラス
# ---------------------------------------------------------------------
class AsyncTracker:
    """
    *record_start* / *record_stop* あるいは *record()* で保持イベントを追加し、
    *snapshot()* で `List[tuple(holder_id, score)]` を得る。
    """
    
    def __init__(self) -> None:
        self._agg = PyAggregator()
        self._pending: Dict[Tuple[str, str], Tuple[int, float]] = {}

    async def record(self, event: HoldEvent) -> None:
        start_ts = int(event.start.timestamp())
        end_ts = int(event.end.timestamp()) if event.end else None
        ev = PyHoldEvent(event.token_id, event.holder_id, start_ts, end_ts, event.weight)
        await self._agg.record(ev)  # type: ignore[arg-type]

    async def record_start(self, token_id: str, holder_id: str, weight: float = 1.0) -> None:
        self._pending[(token_id, holder_id)] = (int(time.time()), weight)

    async def record_stop(self, token_id: str, holder_id: str) -> None:
        key = (token_id, holder_id)
        if key not in self._pending:
            raise RuntimeError(f"No pending start for {key}")
        start_ts, weight = self._pending.pop(key)
        end_ts = int(time.time())
        ev = PyHoldEvent(token_id, holder_id, start_ts, end_ts, weight)
        await self._agg.record(ev)  # type: ignore[arg-type]

    def snapshot(self) -> List[Tuple[str, float]]:
        return self._agg.snapshot()  # type: ignore[return-value]