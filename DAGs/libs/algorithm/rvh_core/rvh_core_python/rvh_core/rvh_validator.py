# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python\rvh_core\rvh_validator.py
"""
rvh_validator.py ― “結果が正しいか” を Python 側だけで再検証する簡易ユーティリティ
"""
"""Rust/Python 選出結果を突き合わせる簡易バリデータ。"""
from __future__ import annotations

from .rvh_builder import rendezvous_hash, RVHError

__all__ = ["validate_selection"]


def validate_selection(nodes, key, k, selected) -> None:
    expected = rendezvous_hash(nodes, key, k)
    if expected != selected:
        raise RVHError(f"selection mismatch: {expected} (expected) vs {selected}")
