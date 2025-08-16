# D:\city_chain_project\network\sending_DAGs\python_sending\continent_level\continent_dag_handler.py

"""
continent_dag_handler.py

大陸DAG：
- 市町村DAGから送られてきたバッチを受信 (HTTPで /push_city_batch)
- バッチを統合し、Rust側の batch_verify 等で検証後、DPoS並列承認を実施
- PoPで地理的に近い大陸ノードを選定し、gRPC送信＋報酬付与
- 承認結果に応じ、次のグローバルDAGへバッチ転送する
"""

import time
import hashlib
import threading
import logging
import random
import requests
from flask import Flask, request, jsonify

from continent_dag_storage import ContinentDAGStorage
from common.config import (
    CONTINENT_BATCH_INTERVAL,
    MAX_DAG_DURATION,
    get_rust_api
)
from common.db_handler import save_completed_tx_to_mongo
from common.node_registry import get_continent_nodes
from common import reward_system

# PoP: ここでは省略せず、従来の pop_stub を利用（または pop_manager.sort_nodes_by_distance）
from consensus import pop_stub

# DPoS python advanced modules
from DPoS.python import dpos_election, dpos_monitor, dpos_advanced
from network.sending_DAG.python_sending.common.grpc import grpc_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
fmt = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
ch.setFormatter(fmt)
logger.addHandler(ch)

app = Flask(__name__)

class ContinentDAGHandler:
    def __init__(self, continent_name: str):
        self.continent_name = continent_name
        self.storage = ContinentDAGStorage()
        self.pending_batches = []
        self.batch_interval = CONTINENT_BATCH_INTERVAL

        self.batch_thread = threading.Thread(target=self._batch_loop, daemon=True)
        self.batch_thread.start()
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

        self.rust_api = get_rust_api()
        self.adv_manager = dpos_advanced.AdvancedDPoSManager()
        self.monitor = dpos_monitor.DPoSMonitor()
        self.reps = self._init_reps()

    def _init_reps(self):
        self.adv_manager.add_stake("ContRepA", 200)
        self.adv_manager.add_stake("ContRepB", 150)
        candidates = [
            {"rep_id": "ContRepA", "metrics": {"access_rate": 1.0, "mem_capacity": 200, "harmony_score": 0.9}},
            {"rep_id": "ContRepB", "metrics": {"access_rate": 0.8, "mem_capacity": 180, "harmony_score": 0.8}},
            {"rep_id": "ContRepC", "metrics": {"access_rate": 0.7, "mem_capacity": 150, "harmony_score": 0.7}}
        ]
        picks = dpos_election.pick_representatives("continent", self.continent_name, candidates, 3, self.adv_manager)
        logger.info("[ContinentDAG] Elected reps: %s", picks)
        return picks

    def _batch_loop(self):
        while True:
            time.sleep(self.batch_interval)
            self._process_batch()

    def _cleanup_loop(self):
        while True:
            time.sleep(5)
            self.storage.cleanup_expired(MAX_DAG_DURATION)

    def add_city_batch(self, batch_id: str, batch_hash: str, tx_list: list):
        self.pending_batches.append({
            "batch_id": batch_id,
            "batch_hash": batch_hash,
            "tx_list": tx_list
        })
        logger.info("[ContinentDAG] Received city batch: %s, hash=%s", batch_id, batch_hash)

    def _process_batch(self):
        if not self.pending_batches:
            return
        joined = self.pending_batches[:]
        self.pending_batches.clear()
        combined_str = ""
        for b in joined:
            combined_str += b["batch_hash"]
        continent_hash = hashlib.sha256(combined_str.encode()).hexdigest()

        # Rust: batch_verify on joined batches (assumed)
        verified_batches = self.rust_api.batch_verify(joined)
        for item in verified_batches:
            self.storage.add_node(
                item["batch_id"],
                {"batch_hash": item["batch_hash"], "tx_list": item["tx_list"]},
                continent_hash
            )
        logger.info("[ContinentDAG] Merged batch: continent_hash=%s, size=%d", continent_hash, len(verified_batches))

        # DPoS
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
        dpos_input = [{"batch_hash": continent_hash, "validators": validators}]
        dpos_res = self.rust_api.dpos_parallel_collect(dpos_input, 0.66)
        if dpos_res:
            r0 = dpos_res[0]
            if r0["approved"]:
                logger.info("[ContinentDAG] DPoS APPROVED: %s", r0["reason"])
                self._shard_and_reward(continent_hash, verified_batches)
                # After approval, push to global DAG can be done via HTTP
                self.push_global_batch(continent_hash, verified_batches)
            else:
                logger.warning("[ContinentDAG] DPoS REJECTED: %s", r0["reason"])
                self.storage.remove_all()  # Remove all pending batches
                for rep_id in r0.get("suspicious_list", []):
                    self.monitor.record_incident(rep_id, "continent multi-phase fail")
                    self.adv_manager.slash(rep_id, "continent_dpos_failure", 0.3)
        else:
            logger.warning("[ContinentDAG] No DPoS result; skipping.")

    def _shard_and_reward(self, continent_hash, verified_batches):
        # PoP: use pop_stub.sort_nodes_by_distance for continent nodes
        # Here, assume get_continent_nodes() returns candidate nodes for the continent
        candidate_nodes = get_continent_nodes(self.continent_name)
        # Use PoP to sort them by distance from a representative sender in the batch:
        sample_tx = verified_batches[0]["tx_list"][0] if verified_batches[0]["tx_list"] else {}
        sender_id = sample_tx.get("sender", "anonymous")
        near_nodes = pop_stub.sort_nodes_by_distance(sender_id, candidate_nodes)
        shard_id = continent_hash[:8]
        for node_info in near_nodes[:2]:
            shard_str = f"ContinentBatch, hash={continent_hash}"
            ok = grpc_client.send_to_node(node_info["node_id"], continent_hash, shard_id, shard_str)
            if ok:
                reward_system.record_contribution(node_info["node_id"], 1.0)

    def push_global_batch(self, continent_hash, verified_batches):
        url = "http://localhost:7001/push_continent_batch"
        data = {
            "continent_batch_id": continent_hash,
            "continent_hash": continent_hash,
            "continent": self.continent_name,
            "batched_data": [b["tx_list"] for b in verified_batches]
        }
        try:
            resp = requests.post(url, json=data, timeout=3)
            if resp.status_code == 200:
                logger.info("[ContinentDAG] push_global_batch: %s", resp.json())
            else:
                logger.warning("[ContinentDAG] push_global_batch failed: code=%d", resp.status_code)
        except Exception as e:
            logger.error("[ContinentDAG] push_global_batch error: %s", e)

@app.route("/push_city_batch", methods=["POST"])
def push_city_batch():
    data = request.get_json()
    batch_id = data.get("batch_id")
    batch_hash = data.get("batch_hash")
    tx_list = data.get("tx_list", [])
    handler = ContinentDAGHandler("Asia")
    handler.add_city_batch(batch_id, batch_hash, tx_list)
    return jsonify({"status": "received", "batch_id": batch_id})

if __name__ == "__main__":
    app.run(port=6001, debug=True)
