# D:\city_chain_project\network\sending_DAGs\python_sending\common\distributed_storage_system.py

"""
distributed_storage_system.py

未完Txなどをファイルとして分散保存する仕組みの例。
単にローカルにJSONを書き込むだけだが、
実際には IPFSやS3、あるいはライトノードへの転送などを行う。
"""

import os
import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
logger.addHandler(ch)

def get_storage_path(node_id: str):
    """
    node_idごとにストレージディレクトリを分ける。
    """
    base = "./dist_storage"
    path = os.path.join(base, node_id)
    os.makedirs(path, exist_ok=True)
    return path

def store_transaction_frag(node_id: str, tx_id: str, shard_id: str, data: dict) -> bool:
    """
    ノードnode_idに対し、tx_id + shard_idのデータを保存する。
    data はdictとしてJSON化。
    """
    folder = get_storage_path(node_id)
    fname = os.path.join(folder, f"{tx_id}_{shard_id}.json")
    try:
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("[DistStorage] %s -> %s 保存完了", node_id, fname)
        return True
    except Exception as e:
        logger.error("[DistStorage] 保存失敗: %s", e)
        return False

def restore_transaction_frag(node_id: str, tx_id: str, shard_id: str) -> dict:
    """
    ノードnode_idにある tx_id+shard_id の断片データを読み出す。
    """
    folder = get_storage_path(node_id)
    fname = os.path.join(folder, f"{tx_id}_{shard_id}.json")
    if not os.path.exists(fname):
        logger.warning("[DistStorage] ファイル未発見: %s", fname)
        return {}
    try:
        with open(fname, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("[DistStorage] 復元成功: %s", fname)
        return data
    except Exception as e:
        logger.error("[DistStorage] 復元失敗: %s", e)
        return {}
