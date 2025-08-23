# config.py
import os
import hashlib

# -------------------------------------------------
# 基本設定（MongoDB接続、バッチ処理、ノード情報など）
# -------------------------------------------------

# MongoDB接続設定（受信完了Tx用）
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "federation_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "completed_transactions")

# バッチ保持時間：DAGに完了Txを保持する期間（秒）
BATCH_INTERVAL = 1

# 分散保存先候補（市町村）
AVAILABLE_MUNICIPALITIES = ["CityA", "CityB", "CityC", "CityD"]

# 分散保存先候補（大陸）
AVAILABLE_CONTINENTS = ["Asia", "Europe", "America", "Africa", "Oceania"]

# 各大陸内のノード候補：
# 各ノードは重み、信頼性、負荷、空き容量（GB）、ノード種別（full/light）を持つ
CONTINENT_NODES = {
    "Asia": [
        {"node_id": "asia_node_1", "weight": 1.2, "reliability": 0.95, "load": 0.3, "capacity": 100, "node_type": "full"},
        {"node_id": "asia_node_2", "weight": 1.0, "reliability": 0.90, "load": 0.2, "capacity": 150, "node_type": "light"},
        {"node_id": "asia_node_3", "weight": 1.1, "reliability": 0.92, "load": 0.4, "capacity": 80, "node_type": "full"}
    ],
    "Europe": [
        {"node_id": "europe_node_1", "weight": 1.0, "reliability": 0.93, "load": 0.35, "capacity": 120, "node_type": "full"},
        {"node_id": "europe_node_2", "weight": 1.3, "reliability": 0.96, "load": 0.25, "capacity": 110, "node_type": "light"}
    ],
    "America": [
        {"node_id": "america_node_1", "weight": 1.1, "reliability": 0.94, "load": 0.3, "capacity": 130, "node_type": "full"},
        {"node_id": "america_node_2", "weight": 1.0, "reliability": 0.92, "load": 0.4, "capacity": 90, "node_type": "light"},
        {"node_id": "america_node_3", "weight": 1.2, "reliability": 0.95, "load": 0.2, "capacity": 140, "node_type": "full"}
    ],
    "Africa": [
        {"node_id": "africa_node_1", "weight": 1.0, "reliability": 0.90, "load": 0.5, "capacity": 70, "node_type": "light"},
        {"node_id": "africa_node_2", "weight": 1.1, "reliability": 0.92, "load": 0.45, "capacity": 60, "node_type": "light"}
    ],
    "Oceania": [
        {"node_id": "oceania_node_1", "weight": 1.2, "reliability": 0.93, "load": 0.3, "capacity": 95, "node_type": "full"},
        {"node_id": "oceania_node_2", "weight": 1.0, "reliability": 0.91, "load": 0.35, "capacity": 85, "node_type": "light"}
    ]
}

# ノード状態更新のハートビート間隔（秒）
HEARTBEAT_INTERVAL = 1

# 報酬設定（Harmony Token）：各ノード種別ごとの報酬倍率
REWARD_RATES = {
    "full": 1.5,
    "light": 1.0
}
TOKEN_REWARD_UNIT = 10  # 各報酬倍率に乗じる単位額

# -------------------------------------------------
# DAG 分散保持のためのシャーディングと冗長保存の設定
# -------------------------------------------------

# シャード数（データを分割する数）
NUM_SHARDS = 4

# 冗長保存するコピー数（各シャードを保存するノード数）
REDUNDANCY = 2

# 例としての利用可能なノードリスト（シミュレーション用）
# ※ 実際は CONTINENT_NODES などから選定する場合もあります。
available_nodes = [
    {"node_id": "node_1", "weight": 1.2, "reliability": 0.95, "capacity": 100},
    {"node_id": "node_2", "weight": 1.0, "reliability": 0.90, "capacity": 150},
    {"node_id": "node_3", "weight": 1.1, "reliability": 0.92, "capacity": 80},
    {"node_id": "node_4", "weight": 1.0, "reliability": 0.93, "capacity": 120},
    # 必要に応じて追加
]


def split_data(data, n):
    """
    データを n 個の断片に均等に分割する。
    シンプルな例として、文字列データを均等に分割します。
    """
    length = len(data)
    chunk_size = length // n
    shards = [data[i * chunk_size:(i + 1) * chunk_size] for i in range(n)]
    if length % n != 0:
        shards[-1] += data[n * chunk_size:]
    return shards


def select_nodes_for_shard(shard, redundancy, nodes):
    """
    シャードごとに、重み付け評価により冗長保存用の 'redundancy' 個のノードを選出します。
    ここでは、シャードのハッシュ値を利用して簡易な重み付き乱数選択を行います。
    """
    shard_hash = int(hashlib.sha256(shard.encode()).hexdigest(), 16)
    scored_nodes = []
    for node in nodes:
        random_factor = (shard_hash % 100) / 100.0  # 0.0〜0.99 の乱数的要素
        score = node["weight"] * node["reliability"] * (1.0 + random_factor)
        scored_nodes.append((score, node))
    scored_nodes.sort(key=lambda x: x[0], reverse=True)
    selected = [n["node_id"] for _, n in scored_nodes[:redundancy]]
    return selected


def shard_and_assign(data, num_shards, redundancy, nodes):
    """
    トランザクションデータを num_shards 個に分割し、
    各断片を redundancy 個のノードに割り当てる。
    戻り値は各シャードのデータと、割り当てられたノードのリストの辞書です。
    """
    shards = split_data(data, num_shards)
    assignments = {}
    for i, shard in enumerate(shards):
        selected_nodes = select_nodes_for_shard(shard, redundancy, nodes)
        assignments[f"shard_{i}"] = {
            "data": shard,
            "assigned_nodes": selected_nodes
        }
    return assignments


# テスト用コード（直接実行した場合のデモ）
if __name__ == "__main__":
    transaction_data = "This is an example transaction data for DAG distributed storage."
    assignments = shard_and_assign(transaction_data, NUM_SHARDS, REDUNDANCY, available_nodes)
    print("断片化および割り当て結果:")
    print(assignments)
