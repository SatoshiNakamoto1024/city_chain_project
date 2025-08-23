# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\calculator.py
"""
保持スコア計算モジュール

* Rust 拡張が import できれば高速版を使用
* 失敗した場合は純 Python 実装にフォールバック
"""

from __future__ import annotations

import logging
from typing import List

from .data_models import HoldEvent  # ← テストで直接使われるモデル
# ---------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Rust 拡張を試行インポート
# ────────────────────────────────────────────────────────────────────
try:
    import poh_holdmetrics_rust as _rust  # type: ignore
except ImportError:  # フォールバック
    _rust = None              # type: ignore
    _HAS_RUST = False
    _logger.warning(
        "Rust extension not found; falling back to pure-Python calculate_score()"
    )
else:
    _HAS_RUST = True
    _logger.debug("Using Rust-accelerated calculate_score()")


# ────────────────────────────────────────────────────────────────────
# パブリック API
# ────────────────────────────────────────────────────────────────────
def calculate_score(events: List[HoldEvent]) -> float:
    """
    与えられた `HoldEvent` のリストから重み付き保持時間の総和を返す。

    * Rust 拡張がロード出来ていればそちらを呼び出す
    * 無ければ純 Python で計算
    """
    if _HAS_RUST and _rust:
        rust_events: list[_rust.PyHoldEvent] = []
        for ev in events:
            start_ts = int(ev.start.timestamp())
            end_ts = int(ev.end.timestamp()) if ev.end else None
            rust_events.append(
                _rust.PyHoldEvent(ev.token_id, ev.holder_id, start_ts, end_ts, ev.weight)
            )
        return _rust.calculate_score(rust_events)

    # -----------------------  Pure-Python 実装 -----------------------
    total = 0.0
    for ev in events:
        if ev.end is None:  # 終了していない保持はスコアに含めない
            continue
        seconds = (ev.end - ev.start).total_seconds()
        total += seconds * ev.weight
    return total


# ────────────────────────────────────────────────────────────────────
# 互換性のため: テストが *位置引数* で生成するケースに対応させる
# （data_models.HoldEvent を拡張する形で monkey-patch）
# ────────────────────────────────────────────────────────────────────
def _enable_positional_args_for_hold_event() -> None:
    """
    `HoldEvent("t", "h", start, end, 1.0)` のような呼び方を
    サポートするために __init__ を差し替える。
    """
    original_init = HoldEvent.__init__  # type: ignore

    def _patched(self, *args, **kwargs):  # type: ignore
        if args:
            kwargs.update(dict(zip(self.model_fields, args, strict=False)))
        original_init(self, **kwargs)

    HoldEvent.__init__ = _patched  # type: ignore


_enable_positional_args_for_hold_event()
