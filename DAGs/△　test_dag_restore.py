#!/usr/bin/env python
# test_dag_restore.py
"""
test_dag_restore.py

このテストスクリプトは、DAG 分散保存されたトランザクションデータの復元（リストア）をシミュレーションします。
1. ダミーの送信トランザクション（DAGNode）を生成し、分散保存（store_transaction）を実行します。
2. 保存されたファイルから、同じ分散保存先情報と tx_id を用いてトランザクションデータを復元（restore_transaction）します。
3. 復元したデータが元のデータと一致するかを確認します。
"""

import time
import random
import hashlib
import json
from uuid import uuid4

# 各モジュールのインポート
from dag.dag_storage import DAGNode
from consensus.distributed_storage import DistributionAlgorithm
from distributed_storage_system import store_transaction, restore_transaction

# ※ ここでは、復元のテスト用に、DistributionAlgorithm を直接利用して
#     分散保存先情報（distribution_info）を算出します。


def create_dummy_transaction():
    """
    ダミーの送信トランザクション（DAGNode）を生成する関数
    """
    tx_id = str(uuid4())
    sender = f"User{random.randint(1, 100)}"
    receiver = f"User{random.randint(101, 200)}"
    amount = random.randint(1, 1000)
    data_str = f"{tx_id}{sender}{receiver}{amount}{time.time()}"
    hash_val = hashlib.sha256(data_str.encode()).hexdigest()
    node = DAGNode(tx_id, sender, receiver, amount, tx_type="send", status="completed")
    node.hash = hash_val  # 生成したハッシュを設定
    return node


def test_restore_transaction():
    """
    ダミーのトランザクションを生成し、保存後に復元テストを実施します。
    """
    # ダミーのトランザクション生成
    dag_node = create_dummy_transaction()

    # DistributionAlgorithm を利用して、分散保存先情報（distribution_info）を算出
    from config import AVAILABLE_MUNICIPALITIES, AVAILABLE_CONTINENTS, CONTINENT_NODES
    algo = DistributionAlgorithm(AVAILABLE_MUNICIPALITIES, AVAILABLE_CONTINENTS, CONTINENT_NODES)
    distribution_info = algo.compute_distribution(dag_node)
    print("算出された分散保存先情報:")
    print(json.dumps(distribution_info, indent=2))

    # トランザクションの保存
    store_transaction(distribution_info, dag_node)

    # 保存後、復元テストを実施
    restored_data = restore_transaction(distribution_info, dag_node.tx_id)
    print("復元されたトランザクションデータ:")
    print(json.dumps(restored_data, indent=2))

    # 簡易的な一致チェック（tx_idが同じかどうか）
    if restored_data and restored_data.get("tx_id") == dag_node.tx_id:
        print("[Test] 復元テスト成功: トランザクションデータが一致しました。")
    else:
        print("[Test] 復元テスト失敗: データが一致しません。")


if __name__ == "__main__":
    test_restore_transaction()
