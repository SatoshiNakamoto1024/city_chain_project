# D:\city_chain_project\network\sending_DAGs\python_sending\common\node_registry.py

"""
node_registry.py

市町村/大陸/グローバルなどのノード情報を一元管理するためのモジュール。
フェデレーションモデルで「市町村ごとに100ノード」「1%がフルノード」などの設定を一括保持。
ここではサンプルとして dict で静的に定義する。
"""

import random

# 例: 10市町村 x 100ノード = 1000ノード, うち1% (10ノード) がfull, etc.

CITY_LIST = [
    "newyork",
    "kanazawa",
    "paris",
    "hongkong",
    "london",
    "tokyo",
    "sydney",
    "toronto",
    "berlin",
    "seoul"
]

NODES_PER_CITY = 100
FULL_NODE_COUNT = 10  # 1% of 1000
LIGHT_NODE_COUNT = (len(CITY_LIST)*NODES_PER_CITY) - FULL_NODE_COUNT

all_nodes = []
node_index = 0
full_node_indices = set(range(FULL_NODE_COUNT))  # simplistic approach

for city in CITY_LIST:
    for i in range(NODES_PER_CITY):
        node_id = f"{city}_node_{i}"
        node_type = "full" if node_index in full_node_indices else "light"
        weight = round(random.uniform(1.0, 1.3), 2)
        reliability = round(random.uniform(0.90, 0.99), 2)
        capacity = random.randint(50, 200)
        all_nodes.append({
            "node_id": node_id,
            "city": city,
            "node_type": node_type,
            "weight": weight,
            "reliability": reliability,
            "capacity": capacity
        })
        node_index += 1

# 大陸リスト
CONTINENTS = ["asia", "europe", "oceania", "africa", "southamerica", "northamerica", "antarctica"]

# 大陸ノードリストを適当に生成(例: 大陸ごとに10ノード)
all_continent_nodes = {}
for c in CONTINENTS:
    c_nodes = []
    for i in range(10):
        node_id = f"{c}_cont_node_{i}"
        node_type = "full" if i < 2 else "light"  # 2フル、8ライト
        weight = round(random.uniform(1.0, 1.5), 2)
        reliability = round(random.uniform(0.88, 0.99), 2)
        capacity = random.randint(100, 500)
        c_nodes.append({
            "node_id": node_id,
            "continent": c,
            "node_type": node_type,
            "weight": weight,
            "reliability": reliability,
            "capacity": capacity
        })
    all_continent_nodes[c] = c_nodes

def get_city_nodes(city_name: str):
    """
    指定したcity_nameに属するノードのリストを返す。
    """
    city_name_lower = city_name.lower()
    city_nodes = [n for n in all_nodes if n["city"] == city_name_lower]
    return city_nodes

def get_continent_nodes(continent_name: str):
    """
    指定した大陸名に属するノードのリストを返す。
    """
    c_name_lower = continent_name.lower()
    return all_continent_nodes.get(c_name_lower, [])
