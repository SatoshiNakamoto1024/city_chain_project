import time
import uuid
import hashlib
import base64
from pathlib import Path
from ..storage.dag_store import DAGStore
from ..core.models import BaseTx, TxType, PoHAckTx
from cert_python import sign_with_cert


class PoHManager:
    MIN_POH = 5  # 副本閾値

    def __init__(self, dag: DAGStore, pem_path: Path):
        self.dag = dag
        self.pem = pem_path

    def build_poh(self, orig: BaseTx, holder_id: str) -> PoHAckTx:
        now = time.time()
        msg = f"{orig.tx_id}|{holder_id}|{now}"
        sig = sign_with_cert(msg, self.pem)
        poh = PoHAckTx(
            tx_id=str(uuid.uuid4()),
            tx_type=TxType.POH_ACK,
            timestamp=now,
            original_tx_id=orig.tx_id,
            holder_id=holder_id,
            storage_hash=hashlib.sha256(orig.json().encode()).hexdigest(),
            signature=base64.b64encode(sig).decode(),
        )
        return poh
