# D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_python\test_rvh.py

import pytest
from rvh_python import rendezvous_hash, RVHError


def test_basic_selection():
    nodes = ["n1", "n2", "n3"]
    key = "key-xyz"
    result = rendezvous_hash(nodes, key, 2)
    assert isinstance(result, list)
    assert len(result) == 2
    # 再実行して同じ結果が返ること
    assert result == rendezvous_hash(nodes, key, 2)


def test_error_empty_nodes():
    with pytest.raises(RVHError):
        rendezvous_hash([], "anykey", 1)


def test_error_k_out_of_range():
    nodes = ["a", "b"]
    with pytest.raises(RVHError):
        rendezvous_hash(nodes, "anykey", 3)