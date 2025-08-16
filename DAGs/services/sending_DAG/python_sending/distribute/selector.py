import random
from typing import List

def pick_next_node(nodes: List[str]) -> List[str]:
    """
    保存先ノードの探索順を決定する
    - 重み付きランダム
    - 地理優先 → 信頼度優先 などプラグイン化可能
    """
    # 例: shuffle して返すだけ（あとで重み付きに）
    shuffled = nodes[:]
    random.shuffle(shuffled)
    return shuffled
