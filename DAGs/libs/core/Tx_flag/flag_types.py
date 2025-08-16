# D:\city_chain_project\network\sending_DAGs\python_sending\Tx_flag\flag_types.py
from enum import Enum

class TxType(str, Enum):
    FRESH_TX    = "fresh_tx"
    POH_ACK     = "poh_ack"
    POH_REQUEST = "poh_request"
    REPAIR_REQ  = "repair_request"
    REPAIR_ACK  = "repair_ack"
    CHECKPOINT  = "checkpoint"
    SYSTEM_TX   = "system_tx"

def classify_tx(tx_dict: dict) -> TxType:
    """
    tx_dict に tx_type キーがあればそれ、無ければ FRESH_TX
    """
    return TxType(tx_dict.get("tx_type", TxType.FRESH_TX))
