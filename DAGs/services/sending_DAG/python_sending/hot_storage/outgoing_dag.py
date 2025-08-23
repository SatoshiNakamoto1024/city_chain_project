# D:\city_chain_project\network\sending_DAGs\python_sending\storage\outgoing_dag.py
"""
送信側では「まだ PoH_ACK が足りない Tx」を保持。
"""
from collections import defaultdict
from typing import Dict, Set
from ..core.models import BaseTx, TxType


class OutgoingDAG:
    def __init__(self):
        self.nodes: Dict[str, BaseTx] = {}
        self.edges: Dict[str, Set[str]] = defaultdict(set)

    def add(self, tx: BaseTx):
        self.nodes[tx.tx_id] = tx

    def add_edge(self, parent: str, child: str):
        self.edges[parent].add(child)

    def count_ack(self, tx_id: str, min_poh: int) -> bool:
        return sum(
            1 for cid in self.edges.get(tx_id, set())
            if self.nodes[cid].tx_type == TxType.POH_ACK
        ) >= min_poh
