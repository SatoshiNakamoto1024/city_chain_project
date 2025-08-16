import time
from prometheus_client import Gauge, push_to_gateway

# Prometheusメトリクス定義
ONLINE_GAUGE = Gauge('dag_online_nodes', '現在オンラインノード数')
AVG_SESSION = Gauge('dag_avg_session_time', '平均セッション時間秒')
GLOBAL_LAT  = Gauge('dag_global_avg_latency', '全体平均PoHレイテンシ秒')

def push_metrics(presence, txmetrics, gateway: str):
    """
    定期的に Prometheus Pushgateway へメトリクスを送信。
    """
    ONLINE_GAUGE.set(presence.get_current_online())
    AVG_SESSION.set(presence.get_global_average_session())
    GLOBAL_LAT.set(txmetrics.get_global_average_latency())
    push_to_gateway(gateway, job='dag_monitor', registry=None)
