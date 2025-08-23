from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class BaseTx(BaseModel):
    tx_id: str = Field(..., min_length=1)
    timestamp: datetime


class FreshTx(BaseTx):
    type: Literal["FRESH_TX"]
    sender: str
    receiver: str
    amount: float = Field(..., gt=0)
    payload: dict


class PoHRequestTx(BaseTx):
    type: Literal["POH_REQUEST"]
    original_tx_id: str
    requester: str

# 他のTxTypeも同様に定義…
