# network/DAGs/common/priority/metrics/login_rate.py

from .base import PriorityMetric


class LoginRateMetric(PriorityMetric):
    """
    ノードの過去一定期間（例：1日）のログイン成功率を元にスコア化。
    node_info['login_rate'] が 0.0〜1.0 の値で与えられる想定。
    """
    def score(self, node_info):
        return float(node_info.get("login_rate", 0.0))
