#!/usr/bin/env python
# test_dag_async.py
"""
test_dag_async.py

このテストスクリプトは、送信トランザクションの DAG 分散保存の処理を
asyncio を利用した非同期並列処理でシミュレーションします。

【処理フロー】
1. 20個のダミー送信トランザクションを生成し、AsyncDAGHandler に非同期に登録します。
2. 各トランザクションは、即座にローカルDAGに登録され、1秒後に非同期バッチ処理が実行され、
   Narwhal/Tusk＋Mysticetiファストパス方式を模倣した分散保存アルゴリズムが起動されます。
3. その後、ダイナミックなシャーディング割り当てのシミュレーションを実行し、結果を出力します。
"""

import asyncio
import time
import random
import hashlib
import json
import copy
from uuid import uuid4

# 各モジュールのインポート
from config import BATCH_INTERVAL, NUM_SHARDS, REDUNDANCY, available_nodes
from dag.dag_storage import DAGNode
from dag.dag_handler import DAGHandler

# ----------------------------
# ネットワーク状態シミュレーション関数
# ----------------------------
def simulate_network_conditions(nodes):
    """
    各ノードの状態をシミュレーションする関数。
    - 各ノードの capacity を ±10% 変動させる。
    - 10% の確率でノードをダウン（up=False）に設定する。
    Returns:
      利用可能な（up==True）ノードのリスト。全てダウンの場合は、変動後の全ノードを返す。
    """
    new_nodes = copy.deepcopy(nodes)
    for node in new_nodes:
        fluctuation = random.uniform(-0.1, 0.1)
        node["capacity"] = max(1, node["capacity"] * (1 + fluctuation))
        node["up"] = random.random() > 0.1
    active_nodes = [node for node in new_nodes if node.get("up", True)]
    if not active_nodes:
        active_nodes = new_nodes
    return active_nodes

# ----------------------------
# シャーディングとノード割り当ての処理（動的シミュレーション版）
# ----------------------------
def split_data(data, n):
    """
    文字列データを n 個の均等な断片に分割する。
    長さが n で割り切れない場合、余剰は最後の断片に追加する。
    """
    length = len(data)
    chunk_size = length // n
    shards = [data[i * chunk_size:(i + 1) * chunk_size] for i in range(n)]
    if length % n != 0:
        shards[-1] += data[n * chunk_size:]
    return shards

def select_nodes_for_shard_dynamic(shard, redundancy, nodes):
    """
    シャードのSHA-256ハッシュ値を計算し、その値に基づいて各ノードにスコアを与え、
    上位 redundancy 件のノードIDを返す。
    """
    shard_hash = int(hashlib.sha256(shard.encode()).hexdigest(), 16)
    scored_nodes = []
    for node in nodes:
        random_factor = (shard_hash % 100) / 100.0
        score = node["weight"] * node["reliability"] * (1.0 + random_factor)
        scored_nodes.append((score, node))
    scored_nodes.sort(key=lambda x: x[0], reverse=True)
    selected = [n["node_id"] for _, n in scored_nodes[:redundancy]]
    return selected

def shard_and_assign_dynamic(data, num_shards, redundancy, nodes):
    """
    入力データを num_shards 個に分割し、各断片に対して、動的なノード状態（simulate_network_conditionsで変動）
    をもとに、上位 redundancy 件のノードを選定する。
    戻り値は、各シャードのデータ、選定されたノード、およびその時点でオンラインの全ノードIDの辞書。
    """
    shards = split_data(data, num_shards)
    assignments = {}
    for i, shard in enumerate(shards):
        dynamic_nodes = simulate_network_conditions(nodes)
        selected_nodes = select_nodes_for_shard_dynamic(shard, redundancy, dynamic_nodes)
        assignments[f"shard_{i}"] = {
            "data": shard,
            "assigned_nodes": selected_nodes,
            "active_nodes": [node["node_id"] for node in dynamic_nodes]
        }
    return assignments

# ----------------------------
# ダミートランザクション生成関数
# ----------------------------
async def create_dummy_transaction():
    """
    ランダムな送信トランザクションを生成し、DAGNode オブジェクトとして返す。
    送信者、受信者、金額はランダムに決定され、トランザクション全体のハッシュ値も計算される。
    """
    tx_id = str(uuid4())
    sender = f"User{random.randint(1, 100)}"
    receiver = f"User{random.randint(101, 200)}"
    amount = random.randint(1, 1000)
    data_str = f"{tx_id}{sender}{receiver}{amount}{time.time()}"
    hash_val = hashlib.sha256(data_str.encode()).hexdigest()
    node = DAGNode(tx_id, sender, receiver, amount, tx_type="send", status="completed")
    node.hash = hash_val
    return node

# ----------------------------
# 各トランザクションの非同期処理関数（並列実行用）
# ----------------------------
async def process_transaction(handler, node):
    """
    1件のトランザクションを非同期に処理する関数。
    ・AsyncDAGHandler.add_transaction を await してDAGに登録し、tx_id と tx_hash を取得。
    ・1秒後のバッチ処理が実行されるのを待機し、
    ・その後、動的なシャーディング割り当てのシミュレーションを実行し、その結果を返す。
    """
    tx_id, tx_hash = await handler.add_transaction(node.sender, node.receiver, node.amount, tx_type="send")
    print(f"登録: tx_id={tx_id}, tx_hash={tx_hash}")
    await asyncio.sleep(BATCH_INTERVAL + 0.3)
    assignments = shard_and_assign_dynamic(node.hash, NUM_SHARDS, REDUNDANCY, available_nodes)
    print(f"Transaction {tx_id} のシャード割り当て結果:")
    print(json.dumps(assignments, indent=2))
    return {
        "tx_id": tx_id,
        "status": "distributed",
        "timestamp": time.time(),
        "assignment": assignments
    }

# ----------------------------
# メイン非同期テスト実行部
# ----------------------------
async def main():
    handler = DAGHandler(batch_interval=BATCH_INTERVAL)
    transactions = [await create_dummy_transaction() for _ in range(20)]
    tasks = [asyncio.create_task(process_transaction(handler, node)) for node in transactions]
    results = await asyncio.gather(*tasks)
    print("=== 非同期並列処理テスト結果 ===")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
