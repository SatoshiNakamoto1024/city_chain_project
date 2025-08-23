# network/DAGs/common/priority/metrics/session_duration.py

from .base import PriorityMetric


class SessionDurationMetric(PriorityMetric):
    """
    ログイン後の平均滞在時間（秒）を正規化してスコア化。
    node_info['avg_session_secs'] を想定。
    """
    # 例：3600秒（1時間）を最大として 1.0 に正規化
    MAX_SECS = 3600

    def score(self, node_info):
        secs = node_info.get("avg_session_secs", 0)
        return min(1.0, secs / self.MAX_SECS)
