"""
reward_system.py

このモジュールは、ネットワークに参加してデータ保存や通信を提供する各ノードに対して、
貢献度に応じた報酬をHarmony Tokenで支払う仕組みを実装します。

報酬額は、ノードの種別（full/light）および、貢献度スコアに基づいて計算されます。
本例では、シンプルなシミュレーションとして、各ノードの報酬をログ出力します。
"""

import random
import threading
from config import REWARD_RATES, TOKEN_REWARD_UNIT, CONTINENT_NODES

node_rewards = {}

def calculate_node_reward(node_info, contribution_score):
    node_type = node_info.get("node_type", "light")
    rate = REWARD_RATES.get(node_type, 1.0)
    reward = contribution_score * rate * TOKEN_REWARD_UNIT
    return reward

def record_node_contribution(node_id, contribution_score):
    node_type = "full" if "full" in node_id or "node_1" in node_id else "light"
    node_info = {"node_id": node_id, "node_type": node_type}
    reward = calculate_node_reward(node_info, contribution_score)
    node_rewards[node_id] = node_rewards.get(node_id, 0) + reward
    print(f"[Reward] ノード {node_id} に {reward:.2f} Harmony Token を支払い、総報酬は {node_rewards[node_id]:.2f} です。")

def distribute_rewards():
    all_nodes = []
    for continent, nodes in CONTINENT_NODES.items():
        for node in nodes:
            all_nodes.append(node["node_id"])
    for node_id in all_nodes:
        contribution = random.uniform(0.5, 1.0)
        record_node_contribution(node_id, contribution)
    threading.Timer(60, distribute_rewards).start()  # 1分ごとに実行

if __name__ == "__main__":
    distribute_rewards()
