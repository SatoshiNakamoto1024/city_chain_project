# network/DAGs/common/priority/composite.py

from .registry import get_metric
from typing import Dict, Any, List, Tuple

class CompositePriority:
    """
    複数の指標を合成して最終スコアを計算し、ソート済みノード一覧を返す。
    weights = {'distance': 0.5, 'login_rate':0.3, 'session_duration':0.2}
    """
    def __init__(self, weights: Dict[str, float]):
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("weights must sum to > 0")
        # 正規化
        self.weights = {k: v/total for k, v in weights.items()}

    def rank_nodes(self, nodes: List[Dict[str,Any]]) -> List[Tuple[Dict,str,float]]:
        scored = []
        for node in nodes:
            score = 0.0
            for name, w in self.weights.items():
                metric = get_metric(name)
                score += w * metric.score(node)
            scored.append((node, score))
        # スコア降順ソート
        return sorted(scored, key=lambda x: x[1], reverse=True)
