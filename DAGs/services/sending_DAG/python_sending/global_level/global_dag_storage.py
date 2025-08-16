# D:\city_chain_project\network\sending_DAGs\python_sending\global_level\global_dag_storage.py

"""
global_dag_storage.py

グローバルDAG用ストレージクラス。
大陸バッチを保持し、期限がきたら削除。
"""

import time

class GlobalDAGStorage:
    def __init__(self):
        self.nodes = {}       # c_batch_id -> dict(continent_hash, data_list, global_hash)
        self.timestamps = {}

    def add_node(self, c_batch_id: str, c_hash: str, continent: str, data_list: list, global_hash: str):
        self.nodes[c_batch_id] = {
            "c_batch_id": c_batch_id,
            "c_hash": c_hash,
            "continent": continent,
            "data_list": data_list,
            "global_hash": global_hash
        }
        self.timestamps[c_batch_id] = time.time()

    def get_node(self, c_batch_id: str):
        return self.nodes.get(c_batch_id)

    def remove_node(self, c_batch_id: str):
        if c_batch_id in self.nodes:
            del self.nodes[c_batch_id]
        if c_batch_id in self.timestamps:
            del self.timestamps[c_batch_id]

    def cleanup_expired(self, max_duration: float):
        now = time.time()
        rm_keys = []
        for k, t0 in self.timestamps.items():
            if now - t0 > max_duration:
                rm_keys.append(k)
        for k in rm_keys:
            self.remove_node(k)
