"""
復元マネージャ:
- trigger_repair() を DApps が呼ぶ
- REPAIR_REQ Tx を生成 (Dilithium 署名)
- Rust verify_and_collect() で PoH/RepairAck を並列検証
"""
import time, uuid, json, base64, threading
from pathlib import Path
from typing import List

from flag_python import TxType, route_tx_by_flag
from poh_python import build_poh_ack              # 既存モジュール
from cert_python import sign_with_cert, verify_signature_with_cert
from .dag_store import DAGStore
from receiving_DAG.rust import recovery as rs_recovery  # pyo3 export

class RecoveryManager:
    MIN_POH = 5

    def __init__(self, pem_path: Path):
        self.pem_path  = pem_path
        self.dag       = DAGStore()
        # 受信キュー（PoH_ACK / REPAIR_ACK）をシンプルに list で模倣
        self.incoming: List[dict] = []
        # 監視スレッド（PoH 蓄積→閾値到達検出）
        threading.Thread(target=self._watch_loop, daemon=True).start()

    # ==== 外部 API ====
    def trigger_repair(self, missing_tx_id: str, requester_id: str):
        ts  = time.time()
        tx  = {
            "tx_id"        : str(uuid.uuid4()),
            "tx_type"      : TxType.REPAIR_REQ.value,
            "missing_tx_id": missing_tx_id,
            "requester"    : requester_id,
            "timestamp"    : ts,
        }
        sig = sign_with_cert(json.dumps(tx, sort_keys=True), self.pem_path)
        tx["signature"] = base64.b64encode(sig).decode()
        self._add_tx(tx)

    # PoH_ACK / REPAIR_ACK をネットワークから push する想定
    def push_incoming(self, tx_dict: dict):
        self.incoming.append(tx_dict)

    # ==== 内部処理 ====
    def _add_tx(self, tx):
        self.dag.add_node(tx)
        if tx["tx_type"] == TxType.POH_ACK.value:
            self.dag.add_edge(tx["original_tx_id"], tx["tx_id"])
        self._route_next(tx)

    def _route_next(self, tx):
        # PoH_ACK: すぐ検証
        if tx["tx_type"] == TxType.POH_ACK.value:
            pub_pem = Path(f"./pem/{tx['holder_id']}.pem")
            ok = verify_signature_with_cert(
                f"{tx['original_tx_id']}|{tx['holder_id']}|{tx['timestamp']}",
                tx["signature"], pub_pem
            )
            if not ok: return
        # REPAIR_ACK: Rust 並列検証
        if tx["tx_type"] == TxType.REPAIR_ACK.value:
            rs_recovery.register_repair_ack(json.dumps(tx))

    def _watch_loop(self):
        while True:
            if self.incoming:
                batch = []
                while self.incoming:
                    batch.append(self.incoming.pop(0))
                # 優先度ソート → DAG 追加
                for t in route_tx_by_flag(batch):
                    self._add_tx(t)
            time.sleep(0.05)
