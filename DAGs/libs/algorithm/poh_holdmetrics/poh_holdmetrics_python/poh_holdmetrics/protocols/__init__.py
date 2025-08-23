# \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\protocols\__init__.py
# -*- coding: utf-8 -*-
"""
poh_holdmetrics.protocols

gRPC / protobuf の生成物 (hold_pb2.py, hold_pb2_grpc.py) を
「トップレベル import」「パッケージ付き import」の両方で使えるようにするブリッジ。
また、旧生成物が参照する `pb.google_dot_protobuf_dot_*` 互換エイリアスも提供。
"""

from __future__ import annotations

# ---- 重要：標準 proto を先に import して descriptor_pool に登録しておく ----
from google.protobuf import timestamp_pb2 as _ts  # noqa: F401
from google.protobuf import empty_pb2 as _empty   # noqa: F401

import importlib
import sys
from types import ModuleType
from typing import Final, List


def _ensure_top_level_alias(top_level: str, qualified: str) -> ModuleType:
    """
    相対 import したモジュールを `sys.modules[top_level]` にも登録。
    `import hold_pb2` と `import poh_holdmetrics.protocols.hold_pb2` を同一化。
    """
    if top_level in sys.modules:
        return sys.modules[top_level]
    module = importlib.import_module(qualified, package=__name__)
    sys.modules[top_level] = module
    return module


# ---- 生成モジュールを読み込み＆トップレベル別名を張る ----
hold_pb2: ModuleType = _ensure_top_level_alias("hold_pb2", ".hold_pb2")
hold_pb2_grpc: ModuleType = _ensure_top_level_alias("hold_pb2_grpc", ".hold_pb2_grpc")

# ---- 旧 grpcio-tools 互換：pb.google_dot_protobuf_dot_* を生やす ----
try:
    if not hasattr(hold_pb2, "google_dot_protobuf_dot_empty__pb2"):
        setattr(hold_pb2, "google_dot_protobuf_dot_empty__pb2", _empty)
except Exception:
    pass

try:
    if not hasattr(hold_pb2, "google_dot_protobuf_dot_timestamp__pb2"):
        setattr(hold_pb2, "google_dot_protobuf_dot_timestamp__pb2", _ts)
except Exception:
    pass

__all__: Final[List[str]] = ["hold_pb2", "hold_pb2_grpc"]

# お掃除
del importlib, sys, ModuleType, _ensure_top_level_alias
