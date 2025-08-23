# D:\city_chain_project\network\sending_DAGs\python_sending\continent_level\continent_dag_storage.py

"""
continent_dag_storage.py

大陸DAG用の簡易ストレージクラス。
市町村から来たバッチをノード化し、期限切れで削除。
"""

import time


class ContinentDAGStorage:
    def __init__(self):
        self.nodes = {}       # batch_id -> dict( batch_hash, tx_list, etc. )
        self.timestamps = {}  # batch_id -> 登録時刻
        self.continent_hash_map = {}  # batch_id -> continent_hash

    def add_node(self, batch_id: str, batch_hash: str, tx_list: list, continent_hash: str):
        self.nodes[batch_id] = {
            "batch_id": batch_id,
            "batch_hash": batch_hash,
            "tx_list": tx_list,
            "continent_hash": continent_hash
        }
        self.timestamps[batch_id] = time.time()
        self.continent_hash_map[batch_id] = continent_hash

    def get_node(self, batch_id: str):
        return self.nodes.get(batch_id)

    def remove_node(self, batch_id: str):
        if batch_id in self.nodes:
            del self.nodes[batch_id]
        if batch_id in self.timestamps:
            del self.timestamps[batch_id]
        if batch_id in self.continent_hash_map:
            del self.continent_hash_map[batch_id]

    def cleanup_expired(self, max_duration: float):
        now = time.time()
        remove_keys = []
        for bid, t0 in self.timestamps.items():
            if now - t0 > max_duration:
                remove_keys.append(bid)
        for bid in remove_keys:
            self.remove_node(bid)
