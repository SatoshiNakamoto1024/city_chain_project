# consensus/distributed_storage.py
import random
import json
import hashlib
import time
import asyncio
import logging
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from distributed_storage_system import store_transaction
from config import AVAILABLE_MUNICIPALITIES, AVAILABLE_CONTINENTS, CONTINENT_NODES

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# --- スマートコントラクト実行のスタブ ---
async def execute_smart_contract(distribution_info, dag_node):
    # 本来はスマートコントラクト実行エンジンが状態更新などを行う
    await asyncio.sleep(0.05)  # 処理遅延を模倣
    logger.info("[SmartContract] Smart contract executed on distribution info: %s", json.dumps(distribution_info))
    # 例として distribution_info に "contract_executed" フラグを追加
    distribution_info["contract_executed"] = True
    return distribution_info

# --- データ可用性証明のスタブ ---
def data_availability_proof(distribution_info):
    # 実際にはデータ可用性証明が行われる
    if random.random() < 0.95:
        logger.info("[DataAvailability] Data available for distribution: %s", json.dumps(distribution_info))
        return True
    else:
        logger.error("[DataAvailability] Data availability proof failed.")
        raise ValueError("Data availability proof failed")

class DistributionAlgorithm:
    def __init__(self, municipalities=AVAILABLE_MUNICIPALITIES,
                 continents=AVAILABLE_CONTINENTS,
                 continent_nodes=CONTINENT_NODES):
        self.municipalities = municipalities
        self.continents = continents
        self.continent_nodes = continent_nodes

    def compute_distribution(self, dag_node):
        try:
            base_hash = int(dag_node.hash, 16)
        except Exception as e:
            logger.error("無効なハッシュ値です: %s", e)
            raise ValueError("無効なハッシュ値です") from e

        municipality = self._select_municipality(base_hash)
        continent = self._select_continent(base_hash)
        node = self._select_node(continent, base_hash)
        distribution_info = {
            "municipality": municipality,
            "continent": continent,
            "node": node,
            "base_hash": base_hash
        }
        logger.info("Distribution computed: %s", json.dumps(distribution_info))
        return distribution_info

    def _select_municipality(self, base_hash):
        index = base_hash % len(self.municipalities)
        return self.municipalities[index]

    def _select_continent(self, base_hash):
        index = (base_hash >> 16) % len(self.continents)
        return self.continents[index]

    def _select_node(self, continent, base_hash):
        nodes = self.continent_nodes.get(continent, [])
        if not nodes:
            logger.warning("No nodes available for continent: %s", continent)
            return "unknown"
        max_capacity = max(node.get("capacity", 0) for node in nodes)
        best_node = None
        best_score = -1.0
        for node in nodes:
            weight = node.get("weight", 1.0)
            reliability = node.get("reliability", 1.0)
            load = node.get("load", 0.0)
            capacity = node.get("capacity", 0)
            capacity_ratio = capacity / max_capacity if max_capacity > 0 else 1.0
            score = weight * reliability * capacity_ratio / (1.0 + load)
            random_adjustment = ((base_hash >> 24) % 100) / 100.0
            score *= (1.0 + random_adjustment)
            if score > best_score:
                best_score = score
                best_node = node["node_id"]
        return best_node if best_node is not None else "unknown"

class ConsensusSimulator:
    def __init__(self, distribution_algo):
        self.distribution_algo = distribution_algo
        self.proposals = []

    def collect_proposal(self, dag_node):
        try:
            proposal = self.distribution_algo.compute_distribution(dag_node)
            # 評価スコア：下位8ビットと乱数の組み合わせ
            score = (((proposal["base_hash"] & 0xFF) / 255.0) * random.uniform(0.9, 1.1))
            proposal["score"] = score
            self.proposals.append(proposal)
            logger.info("[Consensus] 提案収集: %s", json.dumps(proposal))
        except Exception as e:
            logger.error("提案収集エラー: %s", e)

    def finalize_consensus(self, fast_threshold=0.85, normal_threshold=0.5):
        if not self.proposals:
            logger.error("提案がありません")
            raise ValueError("提案がありません")
        avg_score = sum(p["score"] for p in self.proposals) / len(self.proposals)
        logger.info("[Consensus] 平均スコア: %.3f", avg_score)
        if avg_score >= fast_threshold:
            final_proposal = max(self.proposals, key=lambda p: p["score"])
            logger.info("[Consensus] Mysticetiファストパス適用：即時合意")
        else:
            valid = [p for p in self.proposals if p["score"] >= normal_threshold]
            final_proposal = max(valid, key=lambda p: p["score"]) if valid else max(self.proposals, key=lambda p: p["score"])
            logger.info("[Consensus] 通常合意プロセスにより最終合意")
        self.proposals.clear()
        logger.info("[Consensus] 最終合意: %s", json.dumps(final_proposal, indent=2))
        return final_proposal

async def async_consensus_and_distribute(dag_node):
    algo = DistributionAlgorithm(AVAILABLE_MUNICIPALITIES, AVAILABLE_CONTINENTS, CONTINENT_NODES)
    consensus = ConsensusSimulator(algo)
    # 並列実行のシミュレーション：各提案収集処理を非同期で実施
    for _ in range(5):
        consensus.collect_proposal(dag_node)
        await asyncio.sleep(0.1)
    final_distribution = consensus.finalize_consensus(fast_threshold=0.85, normal_threshold=0.5)
    # データ可用性証明のチェック
    data_availability_proof(final_distribution)
    # スマートコントラクト実行による状態更新（並列処理を模倣）
    final_distribution = await execute_smart_contract(final_distribution, dag_node)
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, store_transaction, final_distribution, dag_node)
    except Exception as e:
        logger.error("保存エラー: %s", e)
    return final_distribution

async def distribute_and_save_transaction(dag_node):
    final_distribution = await async_consensus_and_distribute(dag_node)
    return final_distribution

if __name__ == "__main__":
    import asyncio
    class DummyDAGNode:
        def __init__(self, tx_id, hash_val, sender, receiver, amount, tx_type):
            self.tx_id = tx_id
            self.hash = hash_val
            self.sender = sender
            self.receiver = receiver
            self.amount = amount
            self.tx_type = tx_type
            self.timestamp = time.time()
    dummy_data = "advanced dummy data for full consensus simulation with mysticeti fast path"
    dummy_hash = hashlib.sha256(dummy_data.encode()).hexdigest()
    dummy_node = DummyDAGNode("tx_dummy", dummy_hash, "Alice", "Bob", 100, "send")
    distribution = asyncio.run(distribute_and_save_transaction(dummy_node))
    print("最終的な分散保存先情報:")
    print(json.dumps(distribution, indent=2))
