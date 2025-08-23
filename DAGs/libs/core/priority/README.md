じゃあ、どのノードを優先するのか、距離やログイン率や滞在時間などを理論化したもののフォルダー構成とファイル群はどこに配置させれば良い？

ノード選択の「優先度付けロジック」は、他の共通プラグイン群と同じく common/priority/ 配下にまとめるのがおすすめです。
以下のようなフォルダー・ファイル構成で、ご要件の「距離」「ログイン率」「滞在時間」などを分割・理論化し、最終的に合成してランキングを返す設計例を示します。

network/DAGs/core/priority/
├── __init__.py
├── registry.py
├── base.py
├── metrics/
│   ├── __init__.py
│   ├── distance.py
│   ├── login_rate.py
│   └── session_duration.py
└── composite.py

利用例
from network.DAGs.common.priority.composite import CompositePriority

# Presence Service から取得したオンラインノード情報リスト
nodes_info = [
    {"id":"A","distance_km":100,"login_rate":0.9,"avg_session_secs":1800},
    {"id":"B","distance_km":500,"login_rate":0.95,"avg_session_secs": 600},
    # …
]

cp = CompositePriority({
    "distance": 0.5,
    "login_rate": 0.3,
    "session_duration": 0.2
})

ranked = cp.rank_nodes(nodes_info)
for node, score in ranked:
    print(node["id"], score)

まとめ
common/priority/metrics/ 以下に各指標ごとのスコアリング実装を置き

registry.py で動的にロードできるようにし

composite.py で重み付け合成してノード選定ロジックを一本化

これで「距離」「ログイン率」「滞在時間」など、要件に合わせて簡単に追加・入れ替え・重み変更ができる柔軟かつ超高速非同期対応の優先度エンジンが完成します。
