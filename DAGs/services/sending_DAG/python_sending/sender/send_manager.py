# D:\city_chain_project\network\sending_DAGs\python_sending\sender\send_manager.py
"""
送信元全体を統括:
- FRESH_TX 作成
- ノード選定し PoH_REQUEST を撒く
- PoH_ACK が P2P で返ってくる => 未完了DAGへ
"""
import time
import uuid
from pathlib import Path
from typing import Dict
from ...core.models import BaseTx, TxType
from ...storage import OutgoingDAG
from ...network import subscribe
from .node_selector import select_nodes
from .poh_requester import PoHRequester


class SenderManager:
    def __init__(self, pem_path: Path):
        self.dag = OutgoingDAG()
        self.req = PoHRequester(pem_path)
        self.buf: Dict[str, int] = {}
        subscribe(self._on_bus)

    # ---------- DApps 起点 ----------
    def create_tx(self, sender: str, receiver: str, amount: float):
        tx = BaseTx(
            tx_id=str(uuid.uuid4()),
            tx_type=TxType.FRESH_TX,
            timestamp=time.time(),
        )
        self.dag.add(tx)
        nodes = select_nodes(sender, 10)
        self.req.send_requests(tx, nodes)
        self.buf[tx.tx_id] = 0
        return tx.tx_id

    # ---------- PoH_ACK 受信 ----------
    def _on_bus(self, tx_dict: dict):
        if tx_dict["tx_type"] != TxType.POH_ACK.value:
            return
        self.dag.add_edge(tx_dict["original_tx_id"], tx_dict["tx_id"])
        self.buf[tx_dict["original_tx_id"]] += 1
        if self.buf[tx_dict["original_tx_id"]] >= PoHRequester.MIN_POH:
            print(f"[Sender] Tx {tx_dict['original_tx_id']} enough PoH_ACK")
            # 後工程 (市町村DAG) へ渡す etc.
