「0～9 の 10 シャード振り分け」ロジックは、先ほどの全体構成でいうと object_processing モジュールに相当します。具体的には、以下のように配置すると自然です。

    └── python/
        ├── presence/
        ├── object_processing/    ← ここ！
        │   ├── __init__.py
        │   ├── event.py           # イベント／オブジェクトモデル定義
        │   ├── router.py          # Ingress→10 シャード振り分け
        │   └── shard_worker.py    # 各シャードの非同期ワーカー

使い方サンプル
import asyncio
from common.object_processing import IngressRouter, start_workers, BaseEvent

router = IngressRouter()

async def handle(ev: BaseEvent):
    # DAG ノード保存・PoH 計算など
    print("shard", ev.shard_id(), "handled", ev.event_id)

# ワーカー起動
start_workers(router, handle)

async def main():
    # 外部から届いたトランザクションをイベント化してルータへ
    for i in range(100):
        await router.route(BaseEvent(payload={"i": i}))

asyncio.run(main())

# まとめ
event.py
BaseEvent にハッシュベースの shard_id() を実装
10 シャード (可変) へ均等分散

router.py
IngressRouter.route() で 非同期 Queue へ put
queues プロパティで各シャードの Queue が取得可能

shard_worker.py
ShardWorker が Queue を永続監視
start_workers() で全シャード・複数並列ワーカーを一括生成

config.py
SHARD_COUNT / WORKER_CONCURRENCY を環境変数で変更可能

tests/
end-to-end で振り分け＆処理完了を検証（pytest -v で green）

これで sending_DAG / receiving_DAG のフロントで
「大量トランザクションを 10 シャードに自動ルーティング → 並列ワーカーで高速処理」
という基盤が整いました。