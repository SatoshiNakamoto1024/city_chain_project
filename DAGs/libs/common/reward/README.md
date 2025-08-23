5. PoH と報酬アルゴリズムの結合

def on_poh_ack_confirmed(poh):
    score = calc_geo_weight(poh.holder_id, poh.original_tx_id)  # PoP倍率
    reward_system.record_contribution(poh.holder_id, score)
保存した瞬間ではなく、PoH が “accepted” になった瞬間に報酬を確定
スコアは地理距離・オンライン率・TTL まで保持した実績で増加可能

以下を network/DAGs/reward/ にそのまま配置してください。
追加で必要になるユーティリティは calc_geo_weight() を切り出した
geo.py と、Dataclass／Pydantic スキーマを置く schemas.py を補完しました。

network/DAGs/reward/
├── __init__.py
├── config.py
├── geo.py
├── schemas.py
├── reward_system.py
├── app_reward.py
└── test_reward.py

# PoH 受領時に重み付きスコアを計算し、報酬を蓄積する
🎁 Reward サブシステム ― 何をしているか
コンポーネント、	ファイル、	主な責務
データ構造、	schemas.py、	PoH, Contribution dataclass
スコアロジック、	geo.py、	地理距離 Haversine & 係数付きウェイト計算
状態管理、	reward_system.py、	RewardSystem - in-memory スコア表＋（任意）Mongo 永続
外部呼び出し点、	on_poh_ack_confirmed()、	PoH が accepted になった瞬間にスコアを確定
API サービス、	app_reward.py、　	/poh_ack, /score/{node}, /scores
設定、	config.py、　	距離係数・オンライン率係数・TTL 係数・Mongo URI
テスト、	test_reward.py、	FastAPI + httpx (ASGI) で E2E 1 本

1️⃣ PoH → Score の流れ
sequenceDiagram
    participant DAG as Tx DAG
    participant RewardCB as on_poh_ack_confirmed
    participant RS as RewardSystem

    Note over DAG: PoHオブジェクトが<br>“accepted”になった瞬間
    DAG->>RewardCB: on_poh_ack_confirmed(poh,…)
    RewardCB->>RS: record_contribution(holder_id, score)
    RS->>RS: _scores[node] += score
    RS-->>DAG: （任意でMongoにも書込）

スコア計算
score　=　（距離(km)　×　𝑊dist）　+　（オンライン率 × 𝑊online）　+　（TTL ×　𝑊ttl）/3600

係数は config.py で環境変数上書き可。

2️⃣ コードで使う
from network.DAGs.reward.schemas import PoH
from network.DAGs.reward.reward_system import on_poh_ack_confirmed

async def handle_poh_accepted(poh_dict):
    poh = PoH(**poh_dict)          # 必須5フィールドのみ
    on_poh_ack_confirmed(
        poh,
        tx_holder_lat=tx_holder_lat,
        tx_holder_lon=tx_holder_lon,
        online_rate=current_online_rate,
    )

thread-safe: RewardSystem は純 Python なので
asyncio / スレッドでもそのまま呼べます。

3️⃣ REST API として使う
# 起動
python -m network.DAGs.reward.app_reward
# POST PoH_ACK
curl -X POST http://localhost:8082/poh_ack -d '{
  "holder_id": "node-A",
  "original_tx_id": "tx-1",
  "lat": 35.0, "lon": 139.0,
  "ttl_sec": 7200,
  "tx_holder_lat": 34.0,
  "tx_holder_lon": 135.0,
  "online_rate": 0.8
}' -H "Content-Type: application/json"

# GET 個別スコア
curl http://localhost:8082/score/node-A
# GET 全ノード
curl http://localhost:8082/scores

4️⃣ Mongo 永続を有効にする
# reward_system.py 内
_reward_sys = RewardSystem(use_mongo=True)
# もしくは明示インスタンスをアプリに渡して使う
config.MONGO_URI と DB_NAME を環境変数で変更。

5️⃣ テスト戦略
test_reward.py – httpx の ASGITransport で FastAPI を直接呼び出し
/poh_ack → 200
/score/node が正の値
Haversine・TTL・オンライン率が NaN にならないかも検査。

6️⃣ カスタマイズの例
要件	変更点
ノードランキング API	RewardSystem.all_scores() をソートして返す新エンドポイントを app_reward.py に追加
月次リセット	RewardSystem.flush() を cron で呼ぶ or Mongo の Aggregation Pipeline で期間絞り
係数調整	.env or k8s ConfigMap で REWARD_DIST_KM_WEIGHT などを注入
複合スコア	calc_geo_weight() を override し、例: ノードレピュテーション等を追加

#　使い方まとめ
DAG ハンドラで on_poh_ack_confirmed() を呼ぶだけでスコア確定。
REST モードなら app_reward.py をデプロイして
他マイクロサービスは HTTP 叩きでスコア取得。
Mongo オンにすれば履歴も保存され、将来の再計算が容易。

これで PoH 完了 ➜ スコア計上 ➜ 報酬分配 のパイプラインが
シンプルに一貫して運用できます。
