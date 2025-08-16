# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\tx.py

from dataclasses import dataclass

@dataclass
class Tx:
    tx_id:     str
    holder_id: str
    timestamp: float
    payload:   bytes
