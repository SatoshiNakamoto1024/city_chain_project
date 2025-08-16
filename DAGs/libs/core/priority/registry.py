# network/DAGs/common/priority/registry.py

from importlib import import_module

_METRICS = {
    "distance": "network.DAGs.common.priority.metrics.distance.DistanceMetric",
    "login_rate": "network.DAGs.common.priority.metrics.login_rate.LoginRateMetric",
    "session_duration": "network.DAGs.common.priority.metrics.session_duration.SessionDurationMetric",
}

def get_metric(name: str):
    """
    名前から PriorityMetric クラスをロードしてインスタンス化して返す
    """
    path = _METRICS[name]
    module_name, cls_name = path.rsplit(".", 1)
    mod = import_module(module_name)
    cls = getattr(mod, cls_name)
    return cls()
