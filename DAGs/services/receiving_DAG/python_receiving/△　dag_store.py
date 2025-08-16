"""
超簡易 in-memory DAG：未完了Tx と PoH/RepairTx を同一 dict で保持
"""
from collections import defaultdict

class DAGStore:
    def __init__(self):
        self.nodes   = {}              # tx_id -> tx_dict
        self.edges   = defaultdict(set) # parent -> {child...}

    def add_node(self, tx):
        self.nodes[tx["tx_id"]] = tx

    def add_edge(self, parent, child):
        self.edges[parent].add(child)

    def get_children(self, tx_id):
        return self.edges.get(tx_id, set())

    # PoH 数カウント
    def count_poh(self, tx_id):
        return sum(
            1 for c in self.get_children(tx_id)
            if self.nodes[c]["tx_type"] == "poh_ack"
        )
