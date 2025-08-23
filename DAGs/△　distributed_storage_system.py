# distributed_storage_system.py
import os
import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def get_storage_path(distribution_info):
    base_path = "./distributed_storage"
    municipality = distribution_info.get("municipality", "unknown")
    continent = distribution_info.get("continent", "unknown")
    node = distribution_info.get("node", "unknown")
    path = os.path.join(base_path, municipality, continent, node)
    return path


def store_transaction(distribution_info, dag_node):
    path = get_storage_path(distribution_info)
    os.makedirs(path, exist_ok=True)
    data_to_save = {
        "tx_id": dag_node.tx_id,
        "sender": dag_node.sender,
        "receiver": dag_node.receiver,
        "amount": dag_node.amount,
        "timestamp": dag_node.timestamp,
        "hash": dag_node.hash,
        "distribution_info": distribution_info
    }
    filename = os.path.join(path, f"{dag_node.tx_id}.json")
    try:
        with open(filename, "w") as f:
            json.dump(data_to_save, f, indent=2)
        logger.info("[Distributed Storage] 保存完了: %s", filename)
        return True
    except Exception as e:
        logger.error("[Distributed Storage] 保存エラー: %s", e)
        raise


def restore_transaction(distribution_info, tx_id):
    path = get_storage_path(distribution_info)
    filename = os.path.join(path, f"{tx_id}.json")
    try:
        with open(filename, "r") as f:
            data = json.load(f)
        logger.info("[Distributed Storage] 復元成功: %s", filename)
        return data
    except Exception as e:
        logger.error("[Distributed Storage] 復元エラー: %s", e)
        return None


if __name__ == "__main__":
    # 簡単なテスト
    dummy_info = {"municipality": "CityA", "continent": "Asia", "node": "asia_node_1", "base_hash": 12345}
    class Dummy:
        tx_id = "tx_test"
        sender = "Alice"
        receiver = "Bob"
        amount = 100
        timestamp = 1234567890.0
        hash = "dummyhash"
    store_transaction(dummy_info, Dummy)
    restore_transaction(dummy_info, "tx_test")
