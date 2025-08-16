# D:\city_chain_project\network\sending_DAGs\python_sending\common\reward_system.py

"""
reward_system.py

ノードに対して報酬を支払うシミュレーション。
トランザクション保管や通信を引き受けた貢献度に応じて
トークンを付与するなどを想定。
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
import random
import threading
from common.node_registry import all_nodes

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
logger.addHandler(ch)

REWARD_RATES = {
    "full": 1.5,
    "light": 1.0
}
TOKEN_BASE = 10

node_rewards = {}  # node_id -> 累計報酬

def calculate_node_reward(node_type: str, contribution_score: float) -> float:
    rate = REWARD_RATES.get(node_type, 1.0)
    reward = contribution_score * rate * TOKEN_BASE
    return reward

def record_contribution(node_id: str, contribution_score: float):
    """
    ノードの貢献度を加算し、報酬を計算して付与する。
    """
    found = [n for n in all_nodes if n["node_id"] == node_id]
    if not found:
        logger.warning("[Reward] 不明ノード: %s", node_id)
        return
    node_type = found[0]["node_type"]
    rew = calculate_node_reward(node_type, contribution_score)
    node_rewards[node_id] = node_rewards.get(node_id, 0.0) + rew
    logger.info("[Reward] ノード %s に %.2f トークン付与 => 累計 %.2f",
                node_id, rew, node_rewards[node_id])

def distribute_rewards():
    """
    全ノードに対してランダムな貢献度を割り当てるデモ。
    1分ごとに繰り返す。
    """
    for n in all_nodes:
        c_score = random.uniform(0.1, 1.0)
        record_contribution(n["node_id"], c_score)

    # 1分後に再実行
    threading.Timer(60.0, distribute_rewards).start()

if __name__ == "__main__":
    distribute_rewards()
