# D:\city_chain_project\network\sending_DAG\python_sending\city_level\city_dag_storage.py

"""
city_dag_storage.py

市町村DAG用のシンプルなストレージクラス。
未完トランザクションをメモリ上で保持し、期限がきたら削除するだけ。
"""

import time

class CityDAGStorage:
    def __init__(self):
        self.nodes = {}       # tx_id -> dict( sender, receiver, amount, hash, tx_type, etc. )
        self.timestamps = {}  # tx_id -> 登録時刻
        self.batch_hash_map = {} # tx_id -> batch_hash

    def add_node(self, tx_id: str, data: dict, batch_hash: str):
        self.nodes[tx_id] = data
        self.timestamps[tx_id] = time.time()
        self.batch_hash_map[tx_id] = batch_hash

    def get_node(self, tx_id: str):
        return self.nodes.get(tx_id)

    def remove_node(self, tx_id: str):
        if tx_id in self.nodes:
            del self.nodes[tx_id]
        if tx_id in self.timestamps:
            del self.timestamps[tx_id]
        if tx_id in self.batch_hash_map:
            del self.batch_hash_map[tx_id]

    def cleanup_expired(self, max_duration: float):
        """
        max_duration 秒以上経過したTxを強制削除する。
        """
        now = time.time()
        to_remove = []
        for tx_id, t0 in self.timestamps.items():
            if now - t0 > max_duration:
                to_remove.append(tx_id)
        for rid in to_remove:
            self.remove_node(rid)
