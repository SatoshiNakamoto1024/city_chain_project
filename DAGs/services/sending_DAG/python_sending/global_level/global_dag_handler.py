# D:\city_chain_project\network\sending_DAGs\python_sending\global_level\global_dag_handler.py

"""
global_dag_handler.py

グローバルDAG:
- 大陸DAGから送信されたバッチを受信 (/push_continent_batch)
- Rust側の DPoS 最終承認 (multi_phase_dpos) を実施し、
  最終承認されたバッチを immuDB などに保存する
- 必要に応じ、gRPCでシャード送信および報酬付与を実施
"""

import time
import random
import logging
from flask import Flask, request, jsonify

from city_dag_storage import CityDAGStorage
from common.config import get_rust_api
from common.db_handler import save_completed_tx_to_mongo

from DPoS.python import dpos_election, dpos_monitor, dpos_advanced

app = Flask(__name__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
fmt = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
ch.setFormatter(fmt)
logger.addHandler(ch)


class GlobalDAGHandler:
    def __init__(self):
        self.storage = CityDAGStorage()  # 再利用可能なストレージクラス
        self.rust_api = get_rust_api()
        self.adv_manager = dpos_advanced.AdvancedDPoSManager()
        self.monitor = dpos_monitor.DPoSMonitor()
        self.reps = self._init_reps()

    def _init_reps(self):
        self.adv_manager.add_stake("GlobRep1", 300)
        self.adv_manager.add_stake("GlobRep2", 250)
        candidates = [
            {"rep_id": "GlobRep1", "metrics": {"access_rate": 1.0, "mem_capacity": 300, "harmony_score": 0.9, "bandwidth": 12, "uptime": 0.98, "error_rate": 0.02}},
            {"rep_id": "GlobRep2", "metrics": {"access_rate": 0.8, "mem_capacity": 280, "harmony_score": 0.8, "bandwidth": 10, "uptime": 0.95, "error_rate": 0.05}},
            {"rep_id": "GlobRep3", "metrics": {"access_rate": 0.7, "mem_capacity": 200, "harmony_score": 1.0, "bandwidth": 9, "uptime": 0.90, "error_rate": 0.08}}
        ]
        picks = dpos_election.pick_representatives("global", "Earth", candidates, 3, self.adv_manager)
        logger.info("[GlobalDAG] Elected global reps: %s", picks)
        return picks

    def add_continent_batch(self, c_batch_id: str, c_hash: str, c_name: str, data_list: list):
        self.storage.add_node(c_batch_id, {
            "c_hash": c_hash,
            "continent": c_name,
            "data_list": data_list
        }, c_hash)
        self.process_batch(c_batch_id)

    def process_batch(self, batch_id: str):
        node = self.storage.get_node(batch_id)
        if not node:
            return
        c_hash = node["c_hash"]
        c_name = node["continent"]
        data_list = node["data_list"]

        validators = []
        for r in self.reps:
            if r.active and self.monitor.check_validity(r):
                st = self.adv_manager.get_stake(r.rep_id)
                vote_ok = random.choice([True, True, False])
                validators.append({
                    "validator_id": r.rep_id,
                    "stake": st,
                    "online": True,
                    "vote": vote_ok
                })
            else:
                validators.append({
                    "validator_id": r.rep_id,
                    "stake": 0.0,
                    "online": False,
                    "vote": False
                })
        dpos_input = [{"batch_hash": c_hash, "validators": validators}]
        dpos_res = self.rust_api.dpos_parallel_collect(dpos_input, 0.66)
        if dpos_res:
            r0 = dpos_res[0]
            if r0["approved"]:
                logger.info("[GlobalDAG] FINAL DPoS APPROVED: %s", r0["reason"])
                self.storage.remove_node(batch_id)
                self._shard_and_reward(c_hash, data_list)
            else:
                logger.warning("[GlobalDAG] FINAL DPoS REJECTED: %s", r0["reason"])
                self.storage.remove_node(batch_id)
                for rep_id in r0.get("suspicious_list", []):
                    self.monitor.record_incident(rep_id, "global_dpos_fail")
                    self.adv_manager.slash(rep_id, "global_dpos_failure", 0.5)
        else:
            logger.warning("[GlobalDAG] No DPoS result; skipping.")

    def _shard_and_reward(self, c_hash, data_list):
        # グローバル層でのシャーディング・報酬処理（詳細は環境に応じて実装）
        shard_id = c_hash[:8]
        # 例: global ノードに対してgRPC送信を行う（ここでは詳細省略）
        pass

    def mark_batch_completed(self, batch_id: str):
        node = self.storage.get_node(batch_id)
        if not node:
            logger.warning("[GlobalDAG] Batch %s not found", batch_id)
            return
        record = {
            "batch_id": batch_id,
            "continent": node.get("continent"),
            "completed_at": time.time()
        }
        save_completed_tx_to_mongo(record, collection_name="global_completed")
        self.storage.remove_node(batch_id)
        logger.info("[GlobalDAG] Batch %s completed and removed.", batch_id)


global_handler = GlobalDAGHandler()


@app.route("/push_continent_batch", methods=["POST"])
def push_continent_batch():
    data = request.get_json()
    c_batch_id = data.get("continent_batch_id")
    c_hash = data.get("continent_hash")
    c_name = data.get("continent", "Unknown")
    b_data = data.get("batched_data", [])
    global_handler.add_continent_batch(c_batch_id, c_hash, c_name, b_data)
    return jsonify({"status": "global_received", "continent_batch_id": c_batch_id})


if __name__ == "__main__":
    app.run(port=7001, debug=True)
