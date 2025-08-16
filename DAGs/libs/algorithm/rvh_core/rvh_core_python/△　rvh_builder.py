# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_python\rvh_builder.py
"""
rvh_builder.py ― Rendezvous-Hash の実体

* `rvh_rust.rendezvous_hash` があればそちらを呼び出し (≈ 数 10-100 倍速)
* 失敗したら Python 実装 (hashlib.blake2b) へフォールバック
"""
from __future__ import annotations

import hashlib
from typing import List, Sequence

try:
    # Rust バックエンドが事前に `pip install rvh_rust` されていれば使う
    from rvh_rust import rendezvous_hash as _rvh_rust  # type: ignore
    _HAS_RUST = True
except ModuleNotFoundError:           # wheels が無い環境
    _HAS_RUST = False


class RVHError(Exception):
    """Rendezvous Hashing 共通エラー"""
    pass


__all__ = ["rendezvous_hash", "RVHError"]


def rendezvous_hash(nodes: Sequence[str], key: str, k: int) -> List[str]:
    """
    Highest-Random-Weight (Rendezvous) で `key` を `nodes` へ割り当て、
    上位 `k` ノード ID を返す。

    Parameters
    ----------
    nodes : list[str]
        ノード ID 群（重複不可）
    key : str
        オブジェクト／トランザクション ID など任意キー
    k : int
        返すノード数 (1 ≤ k ≤ len(nodes))

    Raises
    ------
    RVHError
        * ノードが空
        * k が範囲外
        * Rust 側で例外発生
    """
    if not nodes:
        raise RVHError("ノードリストが空です")
    if not 1 <= k <= len(nodes):
        raise RVHError(f"k={k} が範囲外です (1..{len(nodes)})")

    if _HAS_RUST:
        try:
            # Rust 版は errors を Python 例外へ map 済
            return _rvh_rust(list(nodes), key, k)  # type: ignore[arg-type]
        except Exception as e:                     # pragma: no cover
            # Rust 例外をそのまま透過
            raise RVHError(str(e)) from e

    # ---- Pure-Python fallback -----------------------------------------
    # Blake2b-128 (digest_size=16) を使用
    scores: list[tuple[int, str]] = []
    key_b = key.encode()
    for node in nodes:
        h = hashlib.blake2b(digest_size=16)
        h.update(node.encode())
        h.update(key_b)
        scores.append((int.from_bytes(h.digest(), "big"), node))

    scores.sort(key=lambda t: t[0], reverse=True)
    return [n for _, n in scores[:k]]
