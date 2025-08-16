# D:\city_chain_project\network\sending_DAGs\python_sending\Tx_flag\flag_router.py
"""
TxType に応じた処理経路を決める簡易ルーター
"""

from .flag_types import TxType
from flag_rust import sorter  # Rust 拡張

PRIORITY_ORDER = [
    TxType.CHECKPOINT,
    TxType.REPAIR_ACK,
    TxType.REPAIR_REQ,
    TxType.POH_ACK,
    TxType.POH_REQUEST,
    TxType.FRESH_TX,
    TxType.SYSTEM_TX,
]

def route_tx_by_flag(tx_list: list[dict]) -> list[dict]:
    """
    TxType の優先度でソートして返す。
    Rust の並列 sorter に渡して高速化。
    """
    # Rust に渡すために (tx_type:str, json_str) の配列に変換
    tuples = [(t["tx_type"], t) for t in tx_list]
    ordered = sorter.sort_by_flag(tuples, [t.value for t in PRIORITY_ORDER])
    return [item for (_, item) in ordered]
