node_list モジュールは “全世界のオンライン中ノード一覧” を管理する共通インフラですから、他のどのレイヤーからも参照できる common 配下に置くのがベストです。今回の構成だと、以下の位置になります：

        └── common/
            ├── __init__.py
            ├── storage_handler/
            ├── presence/               ← Presence Service クライアント
            ├── object_processing/
            └── node_list/             ← ここ！
                ├── __init__.py
                ├── config.py          # 環境変数読み込みと共通定数をまとめる
                ├── schemas.py         # 型安全に取り回すため,dataclass / TypedDict
                ├── manager.py         # Presence Service 経由で “オンライン中ノード” を取得
                ├── registry.py        # 自前キャッシュ／プッシュ更新用 in-memory レジストリ
                └── tests/

manager.py
Presence Service（Redis／etcd／HTTP API）から /presence を叩いて最新リストを取得
ログイン・ログアウト、ハートビートを通じて更新

registry.py
アプリ起動中の「このインスタンスが把握しているオンラインノード一覧」をキャッシュ
TTL／イベント駆動で自動クリア

#　tests/
pip install redis>=4.2.0 aiohttp pytest pytest-asyncio
pip install fastapi uvicorn[standard] aioredis python-dotenv
を先にしておいて、

#　app_node_list.pyを起動方法
export PRESENCE_REDIS_URI="redis://localhost:6379/0"
export PRESENCE_HTTP_PORT=8080   # 任意
python -m network.DAGs.common.node_list.app_node_list

Presence Service をモックした単体テスト
こうしておけば、
storage_handler → node_list で「今どこに保存投げればいいか」の参照
distribute_worker → node_list で「最新オンラインリストを使って分散投げ先を決定」
dag_handler → node_list で「保存完了フラグ付け用 PoH_ACK のターゲット選定」
と、全体のどの層からも一貫して使える “ノードカタログ” として機能します。


1. いま出来上がった “node _list” サブシステムの役割
目的	説明
ノード検出	世界中に散在する全ノードの 「いまオンラインか？」 を 1 秒単位で把握します。
共通カタログ	取得した一覧を NodeRegistry（プロセス内キャッシュ）に保持し、どのレイヤーからでも await get_registry().get_nodes() で即参照できます。
バックエンド抽象化	Presence の実装は
① Redis (SET + TTL)
② HTTP REST (FastAPI + Redis)
の 2 種類。環境変数で切替え可能なので本番／ローカルで同じ API が使えます。
自動同期	start_background_manager() を呼ぶだけで
‣ login → heartbeat → list_nodes
をループする NodeListManager がバックグラウンドで常駐し、Registry を自動更新します。

2. ランタイムの流れ
sequenceDiagram
    participant App
    participant Manager
    participant PresenceSvc
    participant Redis

    App->>Manager: start_background_manager()
    Manager->>PresenceSvc: POST /login (node_id)
    loop every HEARTBEAT_SEC
        Manager->>PresenceSvc: POST /heartbeat
        PresenceSvc->>Redis: 更新 (SET / TTL)
        Manager->>PresenceSvc: GET /presence
        PresenceSvc->>Redis: SMEMBERS + GET
        PresenceSvc-->>Manager: [{node_id, last_seen}...]
        Manager->>Registry: update(nodes)
    end

3. 他レイヤーからの 典型的な使い方パターン
3-1. storage_handler ― 書き込み先シャーディング
from common.node_list.registry import get_registry
import random, httpx

async def save_block(block_json: str):
    nodes = await get_registry().get_nodes()
    if not nodes:
        raise RuntimeError("no online nodes!")

    # 例: CityID が同じノードに寄せるシンプルなハッシュ
    candidate = hash(block_json) % len(nodes)
    target = nodes[candidate].node_id
    url = f"http://{target}:9000/storage"
    async with httpx.AsyncClient() as cli:
        await cli.post(url, json={"block": block_json})

3-2. distribute_worker ― Gossip 送信先の決定
from random import sample
N_PEERS = 8           # 1ラウンドで投げる最大 peer 数

async def gossip(tx):
    peers = await get_registry().get_nodes()
    targets = sample(peers, k=min(N_PEERS, len(peers)))
    for t in targets:
        await send(tx, t.node_id)

3-3. dag_handler ― PoH_ACK を送り返す時のターゲット選択
async def ack(tx_id: str):
    nodes = await get_registry().get_nodes()
    # 例: 先に送信してきたノードの “sender_id” が tx 内に入っている想定
    sender = next((n for n in nodes if n.node_id == tx_id.sender_id), None)
    if sender:
        await send_ack(tx_id, sender.node_id)

4. 主要クラスとメソッド（簡易リファレンス）
クラス / 関数	主なメンバー	用途
NodeInfo	node_id / last_seen	オンラインノード 1 件のレコード
NodeRegistry	await update(nodes) / await get_nodes()	インメモリキャッシュ（TTL 付き）
NodeListManager	run_forever() / stop()	Presence⇄Registry 同期ループ
start_background_manager()	―	Manager のシングルトンを生成し、asyncio.create_task() で常駐開始

5. 環境変数まとめ（config.py で集中管理）
変数	デフォルト	説明
PRESENCE_BACKEND	redis	redis または http
PRESENCE_REDIS_URI	redis://localhost:6379/0	Redis への接続 URI
PRESENCE_HTTP_ENDPOINT	http://localhost:8080/presence	REST API のベース URL
NODE_ID	socket.gethostname()	このノード自身の識別子
NODELIST_HEARTBEAT_SEC	3	Heartbeat 間隔
NODELIST_CACHE_TTL_SEC	10	レジストリ TTL
PRESENCE_HTTP_PORT	8080	FastAPI サーバの待受ポート

6. テスト & 運用 Tips
ユニットテスト：FakePresenceBackend で外部I/Oを完全に切り離し、
pytest -v だけでロジックが壊れていないか確認できます。

統合テスト：docker-compose で
redis:7 + app_node_list.py + pytest を起動し、実機 Redis との疎通を CI で検証する構成が容易。

監視：Presence Service (FastAPI) 側に /metrics を追加し、Prometheus で
オンラインノード数 を可視化すると運用が楽（要 prometheus_fastapi_instrumentator など）。

7. “sending_DAG” 実装に取り込むときの最小ステップ
依存追加
pip install fastapi uvicorn[standard] redis aiohttp

アプリ起動コード（例：main_sending_dag.py）
import asyncio
from common.node_list.manager import start_background_manager
# Presence 同期を開始
start_background_manager()

async def serve():
    # gRPC / HTTP サーバなど sending_DAG 本体を起動
    ...

if __name__ == "__main__":
    asyncio.run(serve())


任意の箇所でレジストリ参照
from common.node_list.registry import get_registry
online = await get_registry().get_nodes()

まとめ
Presence Service が全ノードの生存状態を集約
NodeListManager がバックグラウンドで同期
NodeRegistry がプロセス内キャッシュ
どのレイヤーからも 1 行で 「最新オンラインノード一覧」を取得可能

これを基盤に シャーディング／Gossip／PoH_ACK 送信先選択 など
sending_DAG / receiving_DAG / analytics… あらゆる部分が同じ API で動く

これで “ネットワーク全体の動的なノードカタログ” が完成し、
今後の DAG 処理や負荷分散ロジックをシンプルに実装できるようになりました。
