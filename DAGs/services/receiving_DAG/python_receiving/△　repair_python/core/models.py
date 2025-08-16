from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict

class TxType(str, Enum):
    FRESH_TX     = "fresh_tx"
    POH_REQUEST  = "poh_request"
    POH_ACK      = "poh_ack"
    REPAIR_REQ   = "repair_request"
    REPAIR_ACK   = "repair_ack"
    CHECKPOINT   = "checkpoint"

class BaseTx(BaseModel):
    tx_id: str
    tx_type: TxType = Field(default=TxType.FRESH_TX)
    timestamp: float

class PoHAckTx(BaseTx):
    original_tx_id: str
    holder_id: str
    storage_hash: str
    signature: str

class RepairReqTx(BaseTx):
    missing_tx_id: str
    requester: str
    signature: str

class RepairAckTx(BaseTx):
    original_tx_id: str
    responder: str
    recovered_tx: Dict
    signature: str
