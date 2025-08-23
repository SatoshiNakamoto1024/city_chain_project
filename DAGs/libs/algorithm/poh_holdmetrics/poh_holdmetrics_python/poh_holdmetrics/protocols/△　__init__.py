# \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\protocols\__init__.py
"""
poh_holdmetrics.protocols

gRPC / protobuf の生成物 (hold_pb2.py, hold_pb2_grpc.py) を
「トップレベル import」「パッケージ付き import」の両方で
使えるようにするブリッジ。
"""
from __future__ import annotations
import importlib
import sys
from types import ModuleType
from typing import Final, List, MutableSequence

# 先頭あたりに追加（std types を “ウォームアップ”）
from google.protobuf import timestamp_pb2 as _ts  # noqa: F401
from google.protobuf import empty_pb2 as _empty   # noqa: F401

def _ensure_top_level_alias(top_level: str, qualified: str) -> ModuleType:
    """相対 import したモジュールを `sys.modules[top_level]` にも登録"""
    if top_level in sys.modules:
        return sys.modules[top_level]

    module = importlib.import_module(qualified, package=__name__)
    sys.modules[top_level] = module
    return module


# ------------------------------------------------------------
# protobuf / gRPC 生成モジュールを読み込んでエイリアスを張る
# ------------------------------------------------------------
hold_pb2: ModuleType = _ensure_top_level_alias("hold_pb2", ".hold_pb2")
hold_pb2_grpc: ModuleType = _ensure_top_level_alias("hold_pb2_grpc",
                                                    ".hold_pb2_grpc")

__all__: Final[List[str]] = ["hold_pb2", "hold_pb2_grpc"]


# お掃除
del importlib, sys, ModuleType, _ensure_top_level_alias  # type: ignore
