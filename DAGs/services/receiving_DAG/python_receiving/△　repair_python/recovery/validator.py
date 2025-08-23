from pathlib import Path
from ..core.models import PoHAckTx, RepairAckTx
from cert_python import verify_signature_with_cert


# ---- PoH ----
def verify_poh(poh: PoHAckTx) -> bool:
    pem = Path(f"pem/{poh.holder_id}.pem")
    msg = f"{poh.original_tx_id}|{poh.holder_id}|{poh.timestamp}"
    return verify_signature_with_cert(msg, poh.signature, pem)


# ---- RepairAck ----
def verify_repair_ack(ack: RepairAckTx) -> bool:
    pem = Path(f"pem/{ack.responder}.pem")
    return verify_signature_with_cert(ack.original_tx_id,
                                      ack.signature, pem)
