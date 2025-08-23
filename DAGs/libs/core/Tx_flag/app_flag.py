# D:\city_chain_project\network\sending_DAGs\python_sending\Tx_flag\app_flag.py
from flag_python import TxType, route_tx_by_flag

sample = [
    {"tx_id": "1", "tx_type": TxType.FRESH_TX.value},
    {"tx_id": "2", "tx_type": TxType.POH_ACK.value},
    {"tx_id": "3", "tx_type": TxType.REPAIR_REQ.value},
    {"tx_id": "4", "tx_type": TxType.CHECKPOINT.value},
]

ordered = route_tx_by_flag(sample)
print([t["tx_id"] for t in ordered])
# => ['4', '3', '2', '1']
