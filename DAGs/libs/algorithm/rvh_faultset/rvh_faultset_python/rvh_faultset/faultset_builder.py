# D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_python\rvh_faultset\faultset_builder.py
"""
faultset_builder.py

Geohash でノードをクラスタ分けし、各クラスタに対してフェイルオーバー処理を行います。
Rust バックエンドが入っていれば高速版を、それ以外は Python フォールバックを利用します。
"""

from typing import List, Dict
from .geohash import encode as _geohash_encode

# Rust バックエンドがインストールされていればこちらを使う
try:
    from rvh_faultset_rust import (
        failover as _rs_failover,
        failover_async as _rs_failover_async,
    )
    _USE_RUST = True
except ImportError:
    _USE_RUST = False


class FaultsetError(Exception):
    """フェイルセット処理中に発生する例外"""
    pass


def faultset(
    nodes: List[Dict],
    threshold: float,
    precision: int = 6,
) -> List[str]:
    """
    Geohash で緯度経度をクラスタ化し、各クラスタに対してフェイルオーバーを実行します。
    （同期版）
    """
    if not nodes:
        raise FaultsetError("nodes list is empty")

    # ① 各ノードをジオハッシュでクラスタ分け
    clusters: Dict[str, List[Dict]] = {}
    for n in nodes:
        gh = _geohash_encode(n["lat"], n["lon"], precision)
        clusters.setdefault(gh, []).append(n)

    survivors: List[str] = []

    # ② 各クラスタごとにフェイルオーバー (Rust or Python) を呼び出し
    for group in clusters.values():
        ids = [n["id"] for n in group]
        lats = [n["latency"] for n in group]

        try:
            if _USE_RUST:
                survivors += _rs_failover(ids, lats, threshold)
            else:
                survivors += _python_failover(ids, lats, threshold)
        except FaultsetError:
            # そのクラスタではサバイバー無し → 無視
            continue

    # ③ 最終的に一人も残らなければエラー
    if not survivors:
        raise FaultsetError("all clusters yielded no survivors")

    return survivors


async def faultset_async(
    nodes: List[Dict],
    threshold: float,
    precision: int = 6,
) -> List[str]:
    """
    非同期版: 同期版と同じロジックだが、Rust の failover_async() を await します。
    """
    if not nodes:
        raise FaultsetError("nodes list is empty")

    clusters: Dict[str, List[Dict]] = {}
    for n in nodes:
        gh = _geohash_encode(n["lat"], n["lon"], precision)
        clusters.setdefault(gh, []).append(n)

    survivors: List[str] = []

    for group in clusters.values():
        ids = [n["id"] for n in group]
        lats = [n["latency"] for n in group]

        try:
            if _USE_RUST:
                # 非同期 Rust 実装を呼び出し
                chunk = await _rs_failover_async(ids, lats, threshold)
                survivors += chunk
            else:
                survivors += _python_failover(ids, lats, threshold)
        except FaultsetError:
            continue

    if not survivors:
        raise FaultsetError("all clusters yielded no survivors")

    return survivors


def _python_failover(
    nodes: List[str],
    latencies: List[float],
    threshold: float,
) -> List[str]:
    """
    シンプル Python フォールバック実装。
    latency <= threshold のノードを返し、全件超過なら例外を投げる。
    """
    survivors = [nid for nid, lat in zip(nodes, latencies, strict=False) if lat <= threshold]
    if not survivors:
        raise FaultsetError("all nodes exceed threshold")
    return survivors
