# D:\city_chain_project\network\sending_DAG\python_sending\municipality_level\municipality_dag_handler.py

"""
municipality_dag_handler.py

市町村DAG:
- PoP (Shapely+STRtree) で100~200msを狙う
- Rustで batch_verify / resolve_object_deps
- Rustで DPoS (並列承認)
- gRPC でシャード送信 + 報酬
- OKなら 大陸DAG へバッチを送る (市町村バッチ)
"""

import time
import uuid
import hashlib
import threading
import logging
import random

from city_dag_storage import CityDAGStorage
from common.config import (
    get_dynamic_batch_interval, MAX_DAG_DURATION,
    ALLOW_EXTEND_DURATION, REBALANCE_INTERVAL,
    get_rust_api
)
from common.db_handler import save_completed_tx_to_mongo
from common.node_registry import get_city_nodes
from common import grpc_client, reward_system

# PoP modules
from algorithm.PoP import pop_manager

# Advanced DPoS
from DPoS.python import dpos_election, dpos_monitor, dpos_advanced

# Crypto stubs
from crypto.ntru_stub import ntru_encrypt
from crypto.dilithium_stub import dilithium_sign

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
fmt = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
ch.setFormatter(fmt)
logger.addHandler(ch)

class CityDAGHandler:
    def __init__(self, city_name: str):
        self.city_name = city_name
        self.storage = CityDAGStorage()
        self.pending_txs = []
        self.batch_interval = 1.0

        self.batch_thread = threading.Thread(target=self._batch_loop, daemon=True)
        self.batch_thread.start()
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        self.rebalance_thread = threading.Thread(target=self._rebalance_loop, daemon=True)
        self.rebalance_thread.start()

        # Rust
        self.rust_api = get_rust_api()
        # PoP => shapely
        pop_manager.initialize_pop_system()
        # DPoS => advanced
        self.adv_manager = dpos_advanced.AdvancedDPoSManager()
        self.monitor = dpos_monitor.DPoSMonitor()
        self.reps = self._init_reps()

        # object dependency
        self.object_map_dict = {
            "mapping": {
                "obj_1": {"Owned": "Alice"},
                "obj_2": "Shared",
                "obj_3": "Immutable"
            }
        }

    def _init_reps(self):
        # 例: stake
        self.adv_manager.add_stake("CRep1", 100)
        self.adv_manager.add_stake("CRep2", 120)
        cands = [
            {"rep_id": "CRep1", "metrics": {"access_rate": 0.9, "mem_capacity": 50, "harmony_score": 0.8, "bandwidth": 10, "uptime": 0.95, "error_rate": 0.05}},
            {"rep_id": "CRep2", "metrics": {"access_rate": 0.8, "mem_capacity": 80, "harmony_score": 0.9, "bandwidth": 9, "uptime": 0.90, "error_rate": 0.10}},
            {"rep_id": "CRep3", "metrics": {"access_rate": 0.7, "mem_capacity": 100, "harmony_score": 0.7, "bandwidth": 8, "uptime": 0.85, "error_rate": 0.15}}
        ]
        picks = dpos_election.pick_representatives(
            "municipality", self.city_name, cands, num_reps=3, adv_manager=self.adv_manager
        )
        logger.info("[CityDAG] Elected reps => %s", picks)
        return picks

    def _batch_loop(self):
        while True:
            self.batch_interval = get_dynamic_batch_interval(len(self.pending_txs))
            time.sleep(self.batch_interval)
            self._process_batch()

    def _cleanup_loop(self):
        while True:
            time.sleep(5)
            now = time.time()
            rm = []
            for tx_id in list(self.storage.nodes.keys()):
                t0 = self.storage.timestamps[tx_id]
                if now - t0 > MAX_DAG_DURATION:
                    node_data = self.storage.nodes[tx_id]
                    if ALLOW_EXTEND_DURATION and node_data.get("extension_requested"):
                        logger.info("[CityDAG] Tx %s => 延長", tx_id)
                        self.storage.timestamps[tx_id] = time.time()
                    else:
                        logger.warning("[CityDAG] Tx %s => 期限切れ破棄", tx_id)
                        rm.append(tx_id)
            for rid in rm:
                self.storage.remove_node(rid)

    def _rebalance_loop(self):
        while True:
            time.sleep(REBALANCE_INTERVAL)
            logger.info("[CityDAG] リバランス中...")
            for tx_id, node_data in list(self.storage.nodes.items()):
                sender = node_data["sender"]
                cand_nodes = get_city_nodes(sender)
                shard_id = node_data["hash"][:6]
                for node_info in cand_nodes[:4]:
                    ok = self._send_shard_and_reward(node_info, tx_id, shard_id, node_data)
                    if ok:
                        logger.info("[CityDAG] Rebalance => %s -> node=%s", tx_id, node_info["node_id"])

    def add_transaction(self, sender: str, receiver: str, amount: float, lat=None, lon=None):
        t0 = time.time()
        place_info = pop_manager.get_place_info_and_bonus(sender, lat, lon)
        t1 = time.time()
        pop_time_ms = (t1 - t0) * 1000

        logger.info("[CityDAG] PoPcalc user=%s => lat=%.5f lon=%.5f city=%s mult=%.1f [%.2fms]",
                    sender, place_info["lat"], place_info["lon"],
                    place_info["city_id"], place_info["multiplier"], pop_time_ms)

        raw_str = f"{sender}-{receiver}-{amount}-{time.time()}"
        sig = dilithium_sign(raw_str)
        enc = ntru_encrypt(sig)
        tx_id = str(uuid.uuid4())
        tx_hash = hashlib.sha256(enc.encode()).hexdigest()

        if sender == "Alice":
            read_set = ["obj_2"]
            write_set = ["obj_1"]
        else:
            read_set = ["obj_1"]
            write_set = ["obj_2"]

        tx_data = {
            "tx_id": tx_id,
            "hash": tx_hash,
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "read_set": read_set,
            "write_set": write_set,
            # PoP情報
            "pos_lat": place_info["lat"],
            "pos_lon": place_info["lon"],
            "city_id": place_info["city_id"],
            "pos_multiplier": place_info["multiplier"],
            "pos_method": place_info["method"]
        }
        self.pending_txs.append(tx_data)
        logger.info("[CityDAG] add Tx => %s => pending=%d", tx_id, len(self.pending_txs))
        return tx_id, tx_hash

    def _process_batch(self):
        if not self.pending_txs:
            return
        batch_list = self.pending_txs[:]
        self.pending_txs.clear()

        verified = self.rust_api.batch_verify(batch_list)
        logger.info("[CityDAG] batch_verify => in=%d verified=%d", len(batch_list), len(verified))

        dep_res = self.rust_api.resolve_object_deps(verified, self.object_map_dict)
        if not dep_res:
            logger.warning("[CityDAG] no dep_res => skip")
            return
        accepted = dep_res["accepted"]
        rejected = dep_res["rejected"]
        logger.info("[CityDAG] object_deps => accepted=%d, rejected=%d", len(accepted), len(rejected))

        batch_hash_str = "".join([x["tx"]["hash"] for x in accepted])
        if batch_hash_str:
            bhash = hashlib.sha256(batch_hash_str.encode()).hexdigest()
        else:
            bhash = str(uuid.uuid4())

        for x in accepted:
            txd = x["tx"]
            self.storage.add_node(txd["tx_id"], txd, bhash)

        if accepted:
            # DPoS: 代表者による承認
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
            dpos_input = [{"batch_hash": bhash, "validators": validators}]
            dpos_res = self.rust_api.dpos_parallel_collect(dpos_input, 0.66)
            if dpos_res:
                r0 = dpos_res[0]
                if r0["approved"]:
                    logger.info("[CityDAG] DPoS => APPROVED: batch=%s, reason=%s", bhash, r0["reason"])
                else:
                    logger.warning("[CityDAG] DPoS => REJECT: batch=%s, reason=%s", bhash, r0["reason"])
                    for it in accepted:
                        self.storage.remove_node(it["tx"]["tx_id"])
                    return
            else:
                logger.warning("[CityDAG] dpos => no result => skip")

        # gRPC shard送信 + 報酬
        for rtx in accepted:
            txd = rtx["tx"]
            if not self.storage.get_node(txd["tx_id"]):
                continue
            cand_nodes = get_city_nodes(txd["sender"])
            # Use PoP to sort candidate nodes by distance from sender
            near_nodes = pop_manager.sort_nodes_by_distance(txd["sender"], cand_nodes)
            shard_id = txd["hash"][:6]
            for node_info in near_nodes[:4]:
                ok = self._send_shard_and_reward(node_info, txd["tx_id"], shard_id, txd)
                if ok:
                    logger.info("[CityDAG] shard => node=%s, tx=%s", node_info["node_id"], txd["tx_id"])

        for rx in rejected:
            logger.warning("[CityDAG] REJECT => tx=%s, reason=%s", rx["tx"]["tx_id"], rx["status"])

    def _send_shard_and_reward(self, node_info, tx_id, shard_id, tx_data):
        shard_str = f"{tx_id} read={tx_data['read_set']} write={tx_data['write_set']}"
        ok = grpc_client.send_to_node(node_info["node_id"], tx_id, shard_id, shard_str)
        if ok:
            final_score = tx_data.get("pos_multiplier", 1.0)
            reward_system.record_contribution(node_info["node_id"], final_score)
        return ok

    def push_continent_batch(self, batch_hash: str, accepted_list):
        """
        市町村DAGで承認されたバッチを大陸DAGに転送する。
        ここではHTTP POSTを用いる例（実際はgRPCも可能）。
        """
        url = "http://localhost:6001/push_city_batch"
        data = {
            "batch_id": batch_hash,
            "batch_hash": batch_hash,
            "tx_list": [x["tx"] for x in accepted_list]
        }
        try:
            resp = requests.post(url, json=data, timeout=3)
            if resp.status_code == 200:
                logger.info("[CityDAG] push_city_batch succeeded: %s", resp.json())
            else:
                logger.warning("[CityDAG] push_city_batch failed: code=%d", resp.status_code)
        except Exception as e:
            logger.error("[CityDAG] push_city_batch error: %s", e)

    def mark_transaction_completed(self, tx_id: str):
        node_data = self.storage.get_node(tx_id)
        if not node_data:
            logger.warning("[CityDAG] Tx not found: %s", tx_id)
            return
        record = {
            "tx_id": tx_id,
            "sender": node_data["sender"],
            "receiver": node_data.get("receiver"),
            "amount": node_data.get("amount"),
            "hash": node_data["hash"],
            "read_set": node_data.get("read_set", []),
            "write_set": node_data.get("write_set", []),
            "pos_lat": node_data.get("pos_lat"),
            "pos_lon": node_data.get("pos_lon"),
            "city_id": node_data.get("city_id"),
            "pos_multiplier": node_data.get("pos_multiplier", 1.0),
            "completed_at": time.time(),
            "city": self.city_name
        }
        save_completed_tx_to_mongo(record)
        self.storage.remove_node(tx_id)
        logger.info("[CityDAG] Tx %s completed and removed; record stored.", tx_id)

    def add_raw_tx(self, tx_data: dict):
        """
        外部から送られたPoH, Repair系Txをそのままpendingキューに追加する。
        """
        tx_data.setdefault("read_set", [])
        tx_data.setdefault("write_set", [])
        self.pending_txs.append(tx_data)
        logger.info("[CityDAG] add_raw_tx => type=%s, tx_id=%s", tx_data.get("tx_type"), tx_data.get("tx_id"))