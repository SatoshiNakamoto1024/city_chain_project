# D:\city_chain_project\network\sending_DAGs\python_sending\sender\node_selector.py
"""
ダミー: 送信者 ID から近傍 10 ノードを返す。実運用は PoP 等と連携
"""
import random
def select_nodes(sender: str, k: int = 10):
    return [f"Node_{i}" for i in random.sample(range(100), k)]
