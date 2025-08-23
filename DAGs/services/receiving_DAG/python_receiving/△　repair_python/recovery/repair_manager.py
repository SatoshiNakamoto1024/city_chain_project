import time
import uuid
import base64
import threading
from pathlib import Path
from typing import List, Dict
from ...core.models import RepairReqTx, RepairAckTx, TxType
from ..storage.dag_store import DAGStore
from .validator import verify_repair_ack
from ..network.p2p_bus import broadcast, subscribe
from receiving_DAG_rust import recovery as rs  # pyo3 拡張
from cert_python import sign_with_cert


class RepairManager:
    def __init__(self, dag: DAGStore, pem_path: Path):
        self.dag = dag
        self.pem = pem_path
        self.buf: Dict[str, List[RepairAckTx]] = {}
        subscribe(self._on_bus_msg)
        threading.Thread(target=self._poll_pool,
                         daemon=True).start()

    # ---- DApps 起点 -------------------------------------------------
    def request_repair(self, missing_tx: str, requester: str):
        sig = sign_with_cert(missing_tx, self.pem)
        tx = RepairReqTx(
            tx_id=str(uuid.uuid4()),
            tx_type=TxType.REPAIR_REQ,
            timestamp=time.time(),
            missing_tx_id=missing_tx,
            requester=requester,
            signature=base64.b64encode(sig).decode()
        )
        broadcast(tx.dict())                 # P2P へ流す
        self.dag.add_node(tx)

    # ---- ネット受信 -------------------------------------------------
    def _on_bus_msg(self, tx_dict: dict):
        if tx_dict["tx_type"] != TxType.REPAIR_ACK.value:
            return
        ack = RepairAckTx.parse_obj(tx_dict)
        if not verify_repair_ack(ack):       # 署名検証
            return
        self.dag.add_node(ack)
        rs.register_repair_ack(ack.json())
    # ----------------------------------------------------------------

    def _poll_pool(self):
        """
        Rust 側で一定数集まったら完了通知
        """
        while True:
            time.sleep(0.1)
            for orig_id in list(self.dag.nodes):
                res = rs.collect_valid_ack(1, orig_id)  # 1 本で OK
                if res:
                    print(f"[Repair] tx={orig_id} fully recovered -> next stage")
