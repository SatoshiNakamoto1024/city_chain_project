# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\types.py
from typing import Literal, TypedDict

# PoH 処理結果のラベル
PoHResult = Literal["success", "failure", "timeout"]

# GC 種別のラベル
GCType = Literal["minor", "major"]

# HTTP エンドポイント用ラベル
class HttpLabels(TypedDict):
    method: str
    status: str

# gRPC エンドポイント用ラベル
class GrpcLabels(TypedDict):
    method: str
    status: str

# PoH カウンター／ヒストグラム用ラベル
class PoHLabels(TypedDict):
    result: PoHResult

# GC カウンター用ラベル
class GcLabels(TypedDict):
    type: GCType
