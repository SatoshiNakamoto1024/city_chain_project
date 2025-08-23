じゃあ、つぎは、
2. 再送・重複排除 (Idempotency)
同一 TxID が複数回飛んできても一度だけ処理するデ・デュープ層
送信失敗時は指数バックオフ＋最大 N 回リトライ

これはどこにいれる？フォルダー名と各ファイルの名前とコードを記載して。

Thought for 7 seconds
「再送・重複排除 (Idempotency)」の責務は、バリデート／トランスフォーム→DAG登録の間に入る “ミドルウェア” 層として切り出すのがベストです。
下記のように sending_DAG/python_sending/middleware/idempotency/ フォルダを作り、その中にデ・デュープとリトライのロジックを入れましょう。

city_chain_project/
└── network/
    └── sending_DAG/
        └── python_sending/
            ├── ingest/
            ├── middleware/
            │   └── idempotency/
            │       ├── __init__.py
            │       ├── dedupe.py
            │       ├── retry.py
            │       └── errors.py
            ├── core/
            ├── sender/
            └── …


使い方例（CityDAGHandler に組み込む）

# network/sending_DAG/python_sending/core/handler.py

from network.sending_DAG.python_sending.middleware.idempotency.dedupe import (
    IdempotencyStore, ensure_not_duplicate
)
from network.sending_DAG.python_sending.middleware.idempotency.retry import retry
from network.sending_DAG.python_sending.middleware.idempotency.errors import IdempotencyError

class CityDAGHandler:
    def __init__(self, ..., redis_url: str = "redis://localhost"):
        self.idemp_store = IdempotencyStore(redis_url)
        # 初回起動時に必ず呼ぶ
        asyncio.create_task(self.idemp_store.init())
        ...

    @retry(max_attempts=5, initial_delay=0.1)
    async def add_transaction(self, tx_node):
        # 1) 重複排除
        await ensure_not_duplicate(tx_node.tx_id, self.idemp_store)

        # 2) 本来のDAG登録処理（既存ロジック）
        #    → dbへの保存、PoH_ACK集約 etc.
        ...

この構成なら、

dedupe.py: Redisで一度処理したTxIDを管理し、重複はすぐに弾く

retry.py: 送信失敗時に指数バックオフで再試行

errors.py: 重複検知の例外クラス

を middleware/idempotency/ にまとめ、core/handler.py の add_transaction 前に挟むだけで全体に効果が波及します。
これで「同じTxを２度処理しない」「一時的な送信エラーは自動リトライ」の両要件を簡潔に実現できます。
