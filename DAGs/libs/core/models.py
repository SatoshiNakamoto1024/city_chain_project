# D:\city_chain_project\network\sending_DAGs\python_sending\core\models.py
from enum import Enum
from pydantic import BaseModel, Field


class TxType(str, Enum):
    FRESH_TX = "fresh_tx"
    POH_REQUEST = "poh_request"
    POH_ACK = "poh_ack"      # 受信側が返す
    CHECKPOINT = "checkpoint"


class BaseTx(BaseModel):
    tx_id: str
    tx_type: TxType = Field(default=TxType.FRESH_TX)
    timestamp: float


class PoHRequestTx(BaseTx):
    original_tx_id: str
    requester: str
    signature: str
