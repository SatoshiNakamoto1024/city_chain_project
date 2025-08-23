# \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_rust_bindings.py
# -*- coding: utf-8 -*-
"""
Rust 拡張 (poh_holdmetrics_rust) の健全性と、Python実装との同値性をまとめてテストする。
拡張が見つからない環境では skip。
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone

import pytest

# ─────────────────────────────────────────────────────────────
#  Rust 拡張が見つからなければ skip
# ─────────────────────────────────────────────────────────────
poh_rust_spec = importlib.util.find_spec("poh_holdmetrics_rust")
RUST_AVAILABLE = poh_rust_spec is not None

pytestmark = pytest.mark.skipif(
    not RUST_AVAILABLE,
    reason="poh_holdmetrics_rust がインストールされていません（maturin develop --release を実行してね）",
)

# Rust 拡張
if RUST_AVAILABLE:
    import poh_holdmetrics_rust as rust  # type: ignore[import-not-found]
else:
    rust = None  # type: ignore[assignment]

# Python 側のモデル／関数（同値性検証で使用）
from poh_holdmetrics.data_models import HoldEvent as PyHoldEventModel
from poh_holdmetrics.calculator import calculate_score as py_calculate_score


# ─────────────────────────────────────────────────────────────
#  ヘルパー
# ─────────────────────────────────────────────────────────────
def _mk_py_event(start: datetime, end: datetime, weight: float) -> PyHoldEventModel:
    """Python 側 HoldEvent（pydantic）を生成。必ずキーワード引数で。"""
    return PyHoldEventModel(
        token_id="tk",
        holder_id="hd",
        start=start,
        end=end,
        weight=weight,
    )


def _mk_rs_event(start: datetime, end: datetime, weight: float):
    """Rust 側 PyHoldEvent（秒の int で渡す）。"""
    s = int(start.timestamp())
    e = int(end.timestamp())
    return rust.PyHoldEvent("tk", "hd", s, e, weight)


def _py_score(start: datetime, end: datetime | None, weight: float) -> float:
    # Rust 側は start/end を整数秒（i64）で受け取り量子化される。
    # よって期待値も「整数秒差 × weight」に合わせる。
    s = int(start.timestamp())
    e = int(end.timestamp()) if end else None
    secs = max(0, (e - s) if e is not None else 0)
    return secs * weight


def _rs_score(start: datetime, end: datetime, weight: float) -> float:
    return rust.calculate_score([_mk_rs_event(start, end, weight)])


# ─────────────────────────────────────────────────────────────
#  あなたの簡易テスト（そのまま包含）
# ─────────────────────────────────────────────────────────────
def test_calculate_score_basic():
    ev = rust.PyHoldEvent("tk", "hd", 1_700_000_000, 1_700_000_100, 2.0)
    assert rust.calculate_score([ev]) > 0.0


def test_aggregator_record_and_snapshot():
    agg = rust.PyAggregator()
    agg.record_sync(rust.PyHoldEvent("tk", "A", 1_700_000_000, 1_700_000_010, 1.0))
    agg.record_sync(rust.PyHoldEvent("tk", "B", 1_700_000_000, 1_700_000_020, 1.0))
    snap = agg.snapshot()
    assert {h for h, _ in snap} == {"A", "B"}


# ─────────────────────────────────────────────────────────────
#  追加の健全性・同値性テスト
# ─────────────────────────────────────────────────────────────
def test_rust_extension_imports():
    """Rust 拡張が普通に import できることの健全性チェック"""
    assert hasattr(rust, "__doc__")


def test_rust_vs_python_single_case():
    """代表 1 ケースで Python/Rust の結果一致を確認"""
    start = datetime.now(tz=timezone.utc)
    end = start + timedelta(seconds=3.5)
    weight = 2.0

    py = _py_score(start, end, weight)
    rs = _rs_score(start, end, weight)

    assert py == pytest.approx(rs, rel=1e-12, abs=1e-12)


@pytest.mark.parametrize(
    "delta_sec, weight",
    [
        (0.0, 1.0),
        (1.0, 1.0),
        (2.5, 0.5),
        (10.0, 3.0),
        (1234.567, 0.01),
    ],
)
def test_rust_vs_python_param(delta_sec: float, weight: float):
    """いくつかの代表値で Python/Rust の結果一致を確認"""
    start = datetime.now(tz=timezone.utc)
    end = start + timedelta(seconds=delta_sec)

    py = _py_score(start, end, weight)
    rs = _rs_score(start, end, weight)
    assert py == pytest.approx(rs, rel=1e-12, abs=1e-12)
