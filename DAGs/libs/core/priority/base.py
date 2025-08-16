# network/DAGs/common/priority/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any

class PriorityMetric(ABC):
    """
    単一の指標を計算するベースクラス。
    return: 0.0〜1.0 のスコア（高いほど優先度大）
    """
    @abstractmethod
    def score(self, node_info: Dict[str, Any]) -> float:
        pass
