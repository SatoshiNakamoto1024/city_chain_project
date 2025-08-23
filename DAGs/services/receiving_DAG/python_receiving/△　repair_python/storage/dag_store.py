from collections import defaultdict
from typing import Dict, Set
from ..core.models import BaseTx, TxType


class DAGStore:
    """
    *未完了* Tx を保持する軽量 DAG (隣接リスト方式)
    """
    def __init__(self):
        self.nodes: Dict[str, BaseTx] = {}
        self.edges: Dict[str, Set[str]] = defaultdict(set)

    # --------------- CRUD ---------------
    def add_node(self, tx: BaseTx):
        self.nodes[tx.tx_id] = tx

    def add_edge(self, parent: str, child: str):
        self.edges[parent].add(child)

    def children(self, tx_id: str) -> Set[str]:
        return self.edges.get(tx_id, set())

    # --------------- PoH 集計 ---------------
    def count_poh(self, tx_id: str, min_cnt: int) -> bool:
        """
        parent(tx_id) にぶら下がる POH_ACK ノード数が min_cnt 以上?
        """
        cnt = sum(
            1 for cid in self.children(tx_id)
            if self.nodes[cid].tx_type == TxType.POH_ACK
        )
        return cnt >= min_cnt
