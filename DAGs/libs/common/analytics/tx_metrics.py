from collections import defaultdict
from threading import Lock


class TxMetrics:
    """
    Tx の送信/受信イベントをトラッキングし、
    ・ノードごとの送信回数
    ・全体レイテンシ(送信→PoH_ACK到着)
    ・平均レイテンシ
    を集計するユーティリティ。
    """
    def __init__(self):
        self._lock = Lock()
        self._sent_counts = defaultdict(int)
        self._latencies = defaultdict(list)  # node_id -> [latency, ...]

    def record_send(self, node_id: str):
        with self._lock:
            self._sent_counts[node_id] += 1

    def record_latency(self, node_id: str, latency: float):
        with self._lock:
            self._latencies[node_id].append(latency)

    def get_sent_count(self, node_id: str) -> int:
        with self._lock:
            return self._sent_counts.get(node_id, 0)

    def get_average_latency(self, node_id: str) -> float:
        with self._lock:
            ls = self._latencies.get(node_id, [])
            return (sum(ls) / len(ls)) if ls else 0.0

    def get_global_average_latency(self) -> float:
        with self._lock:
            all_ls = [lat for lst in self._latencies.values() for lat in lst]
            return (sum(all_ls) / len(all_ls)) if all_ls else 0.0
