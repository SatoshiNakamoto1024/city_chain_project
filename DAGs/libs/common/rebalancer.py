"""
rebalancer.py
─────────────
ライトノードがオフラインになった場合にデータ断片を
別ノードへ複製し直す簡易ロジック（デモ用）。

実運用では:
  * オフライン判定 (心拍 or gRPC ping)
  * IPFS / S3 への再アップロード
  * メタデータの DAG 更新

ここでは「*.json が存在しない ⇒ オフライン」と見なす
ごく簡易的な再配置を行う。
"""
from __future__ import annotations

import glob
import logging
import os
import random
from pathlib import Path
from typing import Dict, List

from common import distributed_storage_system as DSS
from common import node_registry as NR

logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)


def _is_node_offline(node_id: str) -> bool:
    """
    デモ: ストレージフォルダが存在しなければオフラインと判断
    """
    path = Path(DSS.get_storage_path(node_id))
    return not path.exists()


def _pick_online_light_nodes(k: int) -> List[str]:
    online = [
        n["node_id"]
        for n in NR.all_nodes
        if n["node_type"] == "light" and not _is_node_offline(n["node_id"])
    ]
    random.shuffle(online)
    return online[:k]


def rebalance_once() -> List[Dict[str, str]]:
    """
    * オフラインライトノードを検出
    * そのノードが保持していたファイルを別のオンラインノードへコピー
    * コピーした一覧を返す
    """
    moved: List[Dict[str, str]] = []
    offline_nodes = [n["node_id"] for n in NR.all_nodes if _is_node_offline(n["node_id"])]

    if not offline_nodes:
        logger.info("No offline nodes detected")
        return moved

    logger.info("offline nodes = %s", offline_nodes)

    for off_id in offline_nodes:
        pattern = os.path.join(DSS.get_storage_path(off_id), "*.json")
        for fname in glob.glob(pattern):
            try:
                tx_id, shard_id = Path(fname).stem.split("_", 1)
            except ValueError:
                continue

            with open(fname, "r", encoding="utf-8") as f:
                data = f.read()

            # 適当なオンラインノードへ 2 カ所複製
            for dest in _pick_online_light_nodes(2):
                dest_path = os.path.join(DSS.get_storage_path(dest), os.path.basename(fname))
                with open(dest_path, "w", encoding="utf-8") as g:
                    g.write(data)
                moved.append({"from": off_id, "to": dest, "file": os.path.basename(fname)})

    logger.info("rebalance moved %d fragments", len(moved))
    return moved
