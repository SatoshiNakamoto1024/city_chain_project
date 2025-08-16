# D:\city_chain_project\network\sending_DAGs\python_sending\sender\poh_requester.py
import time, uuid, base64
from pathlib import Path
from typing import List
from ...core.models import PoHRequestTx, TxType, BaseTx
from cert_python import sign_with_cert
from ...network import send_grpc

class PoHRequester:
    def __init__(self, pem_path: Path):
        self.pem = pem_path

    def send_requests(self, orig_tx: BaseTx, target_nodes: List[str]):
        for node in target_nodes:
            req = self._build_req(orig_tx, node)
            send_grpc(node, req.dict())

    def _build_req(self, orig: BaseTx, node_id: str) -> PoHRequestTx:
        ts  = time.time()
        msg = f"{orig.tx_id}|{node_id}|{ts}"
        sig = sign_with_cert(msg, self.pem)
        return PoHRequestTx(
            tx_id=str(uuid.uuid4()),
            tx_type=TxType.POH_REQUEST,
            timestamp=ts,
            original_tx_id=orig.tx_id,
            requester=node_id,
            signature=base64.b64encode(sig).decode()
        )
