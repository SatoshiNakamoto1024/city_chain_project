# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\test_rvh_integration.py
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent))
print("sys.path =", sys.path)

import rvh_python
print("rvh_python imported:", rvh_python)
import binascii
import pytest
from rvh_python.rvh_builder import rendezvous_hash, RVHError

NODES = [f"node{i}" for i in range(5)]
KEY = "tx-XYZ"

def test_basic_selection():
    sel1 = rendezvous_hash(NODES, KEY, 3)
    assert isinstance(sel1, list)
    assert len(sel1) == 3
    # 安定性チェック：再呼び出しでも同じ結果になる
    sel2 = rendezvous_hash(NODES, KEY, 3)
    assert sel1 == sel2

def test_ordering_monotonic():
    # k=1 のとき最上位が返る
    top = rendezvous_hash(NODES, KEY, 1)[0]
    for k in range(2, 6):
        sel = rendezvous_hash(NODES, KEY, k)
        assert top in sel

def test_error_empty_nodes():
    with pytest.raises(RVHError):
        rendezvous_hash([], KEY, 1)

def test_error_k_too_large():
    with pytest.raises(RVHError):
        rendezvous_hash(NODES, KEY, len(NODES) + 1)
