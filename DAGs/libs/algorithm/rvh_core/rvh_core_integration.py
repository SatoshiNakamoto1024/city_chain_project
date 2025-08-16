# tests/rvh_core_integration.py
"""
パッケージ公開後 (pip install rvh_core) を想定した統合テスト

- Rust バックエンド有無にかかわらず動くこと
- 同期 / 非同期の両 API が安定していること
"""

import asyncio
import os
from random import Random

import pytest

# ------------------------------------------------------------
# インポート（本番では pip install rvh_core で入る想定）
# ------------------------------------------------------------
from rvh_core import rendezvous_hash, arendezvous_hash, RVHError

NODES = [f"node{i}" for i in range(5)]
KEY   = "tx-XYZ"

# ─────────────────────────────────────────────────────────────
# 正常系
# ─────────────────────────────────────────────────────────────
def test_basic_sync_selection() -> None:
    sel1 = rendezvous_hash(NODES, KEY, 3)
    assert isinstance(sel1, list) and len(sel1) == 3

    # 冪等性チェック
    sel2 = rendezvous_hash(NODES, KEY, 3)
    assert sel1 == sel2


@pytest.mark.asyncio
async def test_basic_async_selection() -> None:
    sel1 = await arendezvous_hash(NODES, KEY, 2)
    sel2 = await arendezvous_hash(NODES, KEY, 2)
    assert sel1 == sel2
    assert len(sel1) == 2


def test_ordering_monotonic() -> None:
    top = rendezvous_hash(NODES, KEY, 1)[0]
    for k in range(2, len(NODES) + 1):
        sel = rendezvous_hash(NODES, KEY, k)
        assert top in sel


# ─────────────────────────────────────────────────────────────
# エラー系
# ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "nodes,k",
    [
        ([], 1),                     # ノードが空
        (NODES, len(NODES) + 1),     # k が大きすぎる
    ],
)
def test_errors(nodes, k) -> None:
    with pytest.raises(RVHError):
        rendezvous_hash(nodes, KEY, k)

    # async も同じ挙動
    with pytest.raises(RVHError):
        asyncio.run(arendezvous_hash(nodes, KEY, k))


# ─────────────────────────────────────────────────────────────
# 追加: Rust / Python を強制的に切り替えても落ちないか fuzz
#      （CI で 2 回流すときのサンプル）
# ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("force_py", [True, False])
def test_random_fuzz_under_both_backends(monkeypatch, force_py) -> None:
    if force_py:
        monkeypatch.setenv("RVH_FORCE_PYTHON", "1")
    else:
        monkeypatch.delenv("RVH_FORCE_PYTHON", raising=False)

    rnd = Random(42)
    for _ in range(50):                     # 調整しやすいループ数
        n = rnd.randint(3, 10)
        nodes = [f"n{rnd.randrange(1000)}" for _ in range(n)]
        k = rnd.randint(1, n)
        key = f"obj-{rnd.randrange(10000)}"

        # sync / async 結果が一致するか
        sync_res  = rendezvous_hash(nodes, key, k)
        async_res = asyncio.run(arendezvous_hash(nodes, key, k))
        assert sync_res == async_res
