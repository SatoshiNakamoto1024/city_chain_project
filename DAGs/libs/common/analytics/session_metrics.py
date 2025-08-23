import time
from collections import defaultdict
from threading import Lock


class SessionMetrics:
    """
    ノードのログイン/ログアウトをトラッキングし、
    ・現在オンラインノード数
    ・一人あたりの平均滞在時間
    ・累計ログイン数
    を集計するユーティリティ。
    """
    def __init__(self):
        self._lock = Lock()
        self._login_times = {}           # node_id -> login_timestamp
        self._total_durations = defaultdict(float)  # node_id -> 累計滞在時間
        self._login_counts = defaultdict(int)

    def login(self, node_id: str):
        with self._lock:
            if node_id not in self._login_times:
                now = time.time()
                self._login_times[node_id] = now
                self._login_counts[node_id] += 1

    def logout(self, node_id: str):
        with self._lock:
            if node_id in self._login_times:
                duration = time.time() - self._login_times.pop(node_id)
                self._total_durations[node_id] += duration

    def get_current_online(self) -> int:
        with self._lock:
            return len(self._login_times)

    def get_average_session(self, node_id: str) -> float:
        with self._lock:
            count = self._login_counts.get(node_id, 0)
            total = self._total_durations.get(node_id, 0.0)
            return (total / count) if count else 0.0

    def get_global_average_session(self) -> float:
        with self._lock:
            totals = list(self._total_durations.values())
            counts = list(self._login_counts.values())
            return (sum(totals) / sum(counts)) if sum(counts) else 0.0
