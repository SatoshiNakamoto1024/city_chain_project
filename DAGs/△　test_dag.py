#!/usr/bin/env python
# test_dag.py
"""
test_dag.py

このテストスクリプトは、送信トランザクションの DAG 分散保存の一連の処理をシミュレーションします。
- 20 個のダミー送信トランザクションを生成し、各トランザクションをローカルの DAG に登録します。
- 1秒保持後に、バッチ処理で Narwhal/Tusk＋Mysticetiファストパスを模倣した分散保存アルゴリズムを実行し、
  各トランザクションに対する分散保存先情報（distribution_info）を算出します。
- このテストコードでは、ネットワーク条件やノードの容量、オンライン状態がランダムに変動し、
  ノードダウンのシナリオもシミュレーションします。
- 算出された情報は、独自の分散ストレージシステムモジュールを通じてファイルとして保存される（※ここではログ出力で確認）。
"""

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
from consensus.distributed_storage import distribute_and_save_transaction

# ----------------------------
# ネットワーク状態のシミュレーション
# ----------------------------

def simulate_network_conditions(nodes):
    """
    各ノードの状態をシミュレーションします。
    - 各ノードの capacity を ±10% ランダムに変動
    - 10% の確率でノードを「ダウン」（up=False）に設定
    """
    new_nodes = copy.deepcopy(nodes)
    for node in new_nodes:
        # 容量の変動（±10%）
        fluctuation = random.uniform(-0.1, 0.1)
        node["capacity"] = max(1, node["capacity"] * (1 + fluctuation))
        # オンライン状態: 90% の確率で up、10% の確率で down
        node["up"] = random.random() > 0.1
    # 利用可能な（up == True）ノードを返す。もしすべてダウンなら全体を返す。
    active_nodes = [node for node in new_nodes if node.get("up", True)]
    if not active_nodes:
        active_nodes = new_nodes
    return active_nodes

# ----------------------------
# シャーディングとノード割り当ての処理（ダイナミック版）
# ----------------------------

def split_data(data, n):
    """
    データを n 個の断片に均等に分割する関数（シンプルな均等分割の例）
    """
    length = len(data)
    chunk_size = length // n
    shards = [data[i * chunk_size:(i + 1) * chunk_size] for i in range(n)]
    if length % n != 0:
        shards[-1] += data[n * chunk_size:]
    return shards

def select_nodes_for_shard_dynamic(shard, redundancy, nodes):
    """
    シャードのハッシュ値を使って、重み付け評価を行い、
    冗長保存用に 'redundancy' 個のノードを選出する。
    ※ ノードリストはすでにオンライン状態のもの（simulate_network_conditions で絞られたもの）を使用する。
    """
    shard_hash = int(hashlib.sha256(shard.encode()).hexdigest(), 16)
    scored_nodes = []
    for node in nodes:
        random_factor = (shard_hash % 100) / 100.0  # 0.0〜0.99 の乱数的要素
        score = node["weight"] * node["reliability"] * (1.0 + random_factor)
        scored_nodes.append((score, node))
    # スコアの高い順に並べる
    scored_nodes.sort(key=lambda x: x[0], reverse=True)
    # 上位 redundancy 個を選ぶ
    selected = [n["node_id"] for _, n in scored_nodes[:redundancy]]
    return selected

def shard_and_assign_dynamic(data, num_shards, redundancy, nodes):
    """
    トランザクションデータを断片化し、各断片に対して、シミュレーションされた動的なノード状態で
    冗長保存先を選出する。
    戻り値は、各シャードのデータと、割り当てられたノードのリストの辞書です。
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
# テスト実行部
# ----------------------------

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

def test_distributed_storage():
    # DAGHandler の初期化（バッチ保持時間 BATCH_INTERVAL 秒）
    dag_handler = DAGHandler(batch_interval=BATCH_INTERVAL)
    transactions = []
    results = []
    
    # 20個のダミー送信トランザクションを生成
    for _ in range(20):
        node = create_dummy_transaction()
        transactions.append(node)
    
    # 各トランザクションについて DAGHandler に登録し、1秒後のバッチ処理を待つ
    for node in transactions:
        tx_id, tx_hash = dag_handler.add_transaction(node.sender, node.receiver, node.amount, tx_type="send")
        print(f"登録: tx_id={tx_id}, tx_hash={tx_hash}")
        time.sleep(1.1)  # バッチ処理が実行されるまで待機
        
        # シミュレーション：トランザクションのハッシュ値を利用して、動的なシャーディング割り当てを実行
        # （実際の分散保存処理は dag_handler 内や consensus で行われるが、ここではダイナミックな割り当てを確認）
        assignments = shard_and_assign_dynamic(node.hash, NUM_SHARDS, REDUNDANCY, available_nodes)
        print(f"Transaction {tx_id} のシャード割り当て結果:")
        print(json.dumps(assignments, indent=2))
        
        result = {
            "tx_id": tx_id,
            "status": "distributed",
            "timestamp": time.time(),
            "assignment": assignments
        }
        results.append(result)
    
    print("=== テスト結果 ===")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    test_distributed_storage()
