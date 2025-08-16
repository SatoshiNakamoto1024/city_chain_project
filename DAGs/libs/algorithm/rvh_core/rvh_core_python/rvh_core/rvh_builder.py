# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python\rvh_core\rvh_builder.py
"""
rvh_builder.py — Rendezvous-Hash (HRW) 実装
------------------------------------------
優先順位
1. rvh_core_rust がインポート出来て、かつ RVH_FORCE_PYTHON が未設定
2. それ以外は pure-Python 実装
"""
from __future__ import annotations

import os
import asyncio
import hashlib
from typing import List, Sequence

# ────────────────────────────────────────────────────────────────
# Rust バックエンドを使うか判定
#   * RVH_FORCE_PYTHON=1 があれば **必ず** pure-Python を使う
# ────────────────────────────────────────────────────────────────
_FORCE_PY = os.getenv("RVH_FORCE_PYTHON") == "1"
_HAS_RUST = False
if not _FORCE_PY:                          # ← ここが肝
    try:
        from rvh_core_rust import (
            rendezvous_hash        as _rvh_sync,
            rendezvous_hash_async  as _rvh_async,
        )
        _HAS_RUST = True
    except ModuleNotFoundError:
        pass  # wheels が無い環境 → Python fallback

class RVHError(Exception):
    """Rendezvous-Hash 共通エラー"""

__all__ = ["rendezvous_hash", "arendezvous_hash", "RVHError"]

# ─── 入力チェック ────────────────────────────────────────────────
def _check(nodes: Sequence[str], k: int) -> None:
    if not nodes:
        raise RVHError("ノードリストが空です")
    if not 1 <= k <= len(nodes):
        raise RVHError(f"k={k} が範囲外です (1..{len(nodes)})")

# ─── Pure-Python 実装 (key → node, little-endian) ───────────────
def _py_sync(nodes: Sequence[str], key: str, k: int) -> List[str]:
    key_b = key.encode()
    scored: list[tuple[int, str]] = []

    for n in nodes:
        h = hashlib.blake2b(digest_size=16)      # BLAKE2b-128
        h.update(key_b)                          # key → node
        h.update(n.encode())
        score = int.from_bytes(h.digest(), "little")
        scored.append((score, n))

    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [n for _, n in scored[:k]]

async def _py_async(nodes: Sequence[str], key: str, k: int) -> List[str]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _py_sync, nodes, key, k)

# ─── Rust ラッパ ────────────────────────────────────────────────
def _rust_sync(nodes: Sequence[str], key: str, k: int) -> List[str]:
    try:
        return _rvh_sync(list(nodes), key, k)          # type: ignore[arg-type]
    except Exception as e:                             # pragma: no cover
        raise RVHError(str(e)) from e

async def _rust_async(nodes: Sequence[str], key: str, k: int) -> List[str]:
    try:
        return await _rvh_async(list(nodes), key, k)   # type: ignore[arg-type]
    except Exception as e:                             # pragma: no cover
        raise RVHError(str(e)) from e

# ─── Public API ────────────────────────────────────────────────
def rendezvous_hash(nodes: Sequence[str], key: str, k: int) -> List[str]:
    _check(nodes, k)
    return _rust_sync(nodes, key, k) if _HAS_RUST else _py_sync(nodes, key, k)

async def arendezvous_hash(nodes: Sequence[str], key: str, k: int) -> List[str]:
    _check(nodes, k)
    return await (_rust_async(nodes, key, k) if _HAS_RUST else _py_async(nodes, key, k))
