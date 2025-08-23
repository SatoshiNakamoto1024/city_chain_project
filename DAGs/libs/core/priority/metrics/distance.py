# network/DAGs/common/priority/metrics/distance.py

from . import base


class DistanceMetric(base.PriorityMetric):
    """
    送信者→保存ノード間の地理距離からスコアを算出。
    node_info['distance_km'] を前提とし、
    距離が近いほど高スコア（1.0）に正規化。
    """
    MAX_DISTANCE = 20000  # 地球周長の半分程度

    def score(self, node_info):
        d = node_info.get("distance_km", self.MAX_DISTANCE)
        # 0km→1.0, MAX_DISTANCE→0.0
        return max(0.0, 1.0 - (d / self.MAX_DISTANCE))
