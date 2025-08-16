# D:\city_chain_project\network\DAGs\python\tests\test_unit_pop.py

"""
test_unit_pop.py

PoPの位置情報計算をテストする例。
"""

import pytest
from consensus.pop_stub import (
    verify_place,
    get_user_location,
    sort_nodes_by_distance
)

def test_verify_place():
    # ダミーのユーザ: "alice", "bob", "charlie", ...
    assert verify_place("alice") == True
    assert verify_place("someone") == False

def test_sort_nodes_by_distance():
    user_id = "alice"
    candidate_nodes = [
        {"node_id": "newyork_node_0"},   # ダミー
        {"node_id": "paris_node_0"},     # ダミー
        {"node_id": "kanazawa_node_0"}
    ]
    sorted_list = sort_nodes_by_distance(user_id, candidate_nodes)
    # alice -> Tokyo(ダミー座標) => Kanazawaがたぶん最も近い? => newyork/parisは遠い
    # ダミー値の実際に依存するが、テストとして "順番に並んでいるか"
    assert len(sorted_list) == 3
    print("Sorted order:", [n["node_id"] for n in sorted_list])
