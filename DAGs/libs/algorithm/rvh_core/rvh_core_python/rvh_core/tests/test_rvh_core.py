# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_python\rvh_core\tests\test_rvh_core.py

import asyncio
import pytest

from rvh_core import rendezvous_hash, arendezvous_hash, RVHError


def test_sync_basic():
    nodes = ["a", "b", "c"]
    sel = rendezvous_hash(nodes, "key", 2)
    assert len(sel) == 2
    # determinism
    assert sel == rendezvous_hash(nodes, "key", 2)


@pytest.mark.asyncio
async def test_async_basic():
    nodes = ["x", "y", "z"]
    sel1 = await arendezvous_hash(nodes, "k1", 1)
    sel2 = await arendezvous_hash(nodes, "k1", 1)
    assert sel1 == sel2


def test_errors():
    with pytest.raises(RVHError):
        rendezvous_hash([], "k", 1)

    with pytest.raises(RVHError):
        rendezvous_hash(["n1"], "k", 2)

    with pytest.raises(RVHError):
        # async error bubbles
        asyncio.run(arendezvous_hash(["n1"], "k", 2))
