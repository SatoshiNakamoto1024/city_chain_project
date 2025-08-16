# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_python\rvh_validator.py
"""
rvh_validator.py ― “結果が正しいか” を Python 側だけで再検証する簡易ユーティリティ
"""
from __future__ import annotations

from .rvh_builder import rendezvous_hash, RVHError


__all__ = ["validate_selection"]


def validate_selection(
    nodes: list[str],
    key: str,
    k: int,
    selected: list[str],
) -> None:
    """
    Rust / Python で生成した `selected` が正しいかをチェック。

    Raises
    ------
    RVHError
        不一致の場合
    """
    expected = rendezvous_hash(nodes, key, k)
    if expected != selected:
        raise RVHError(f"選出不一致: expected={expected}, got={selected}")
