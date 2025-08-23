    │   ├── utils/                       # 全体共通知識
    │   │   ├── __init__.py
    │   │   ├── tx_types.py              # TxType 列挙
    │   │   ├── dag_utils.py             # 共通 DAG ヘルパー
    │   │   ├── constants.py             # 定数定義
    │   │   ├── errors.py                # エラー定義

# utils モジュールの役割 ― 「共通知識のワンストップ・ライブラリ」
ファイル、	ひと言で、	主な責務・ポイント
tx_types.py、	列挙型、	フェデレーション全体で使うトランザクション種別を Enum で集中管理。TxType.has_value() で文字列→列挙の存在確認がワンライナー。
dag_utils.py、	DAG 操作、	- エッジリスト → 隣接リスト変換
- トポロジカルソート（Kahn 法）
- サイクル検出（DFS）
すべて型変数 T で実装しているので文字列でも UUID でも利用可。
constants.py、	定数集、	ノード数上限・デフォルト再試行回数・バックオフ秒など、コード中に “魔法数” を散らさないための一元定義。
errors.py、	共通例外、	アプリ全体で使う基底例外 AppError、DAG サイクル用 DAGCycleError、TxType 不正用 InvalidTxTypeError を定義。統一的なハンドリングが可能。
app_utils.py、	デモ API、	上記ユーティリティを HTTP で試せる FastAPI。DAG 操作や TxType 妥当性チェックを REST 経由で呼び出せる。
test_utils.py、	E2E テスト、	asgi-lifespan + httpx で API 起動→呼び出し→停止 までを本番同等に検証。ユーティリティ関数レベルのロジック＋例外ハンドラ＋エンドポイントを一括テスト。

1. ライブラリとしての使い方
from network.DAGs.common.utils import tx_types as tt
from network.DAGs.common.utils.dag_utils import topological_sort, detect_cycle, flatten_edges
from network.DAGs.common.utils.constants import SHARD_SIZE_LIMIT
from network.DAGs.common.utils.errors import DAGCycleError

# TxType 判定
if not tt.TxType.has_value("TRANSFER"):
    raise tt.InvalidTxTypeError("unsupported")

# DAG トポソート
edges = [("A", "B"), ("A", "C"), ("B", "D")]
graph = flatten_edges(edges)

if detect_cycle(graph):
    raise DAGCycleError("Graph has cycle!")

order = topological_sort(graph)
print("処理順:", order)

# 定数利用
print("1 シャード上限:", SHARD_SIZE_LIMIT, "bytes")

2. API サービスとしての使い方
# 起動
python -m network.DAGs.common.utils.app_utils  # デフォルト :8080
メソッド	パス	機能
GET /tx_types	列挙型一覧
GET /tx_types/validate?value=	文字列が有効な TxType か確認
POST /dag/sort	{ "edges": [["A","B"], ...] } → トポロジカル順
POST /dag/detect_cycle	サイクル有無を bool で返却
POST /dag/flatten	エッジ → 隣接リスト dict
GET /constants	共通定数を JSON で取得
GET /errors/dag_cycle	400 で DAGCycleError 例示
GET /errors/invalid_tx	422 で InvalidTxTypeError 例示

ブラウザで http://localhost:8080/docs を開けば Swagger UI で全エンドポイントを即試せます。

3. テスト
pip install httpx asgi-lifespan
pytest -v network/DAGs/common/utils/test_utils.py

TxType：列挙一覧・バリデーション
DAG Utils：ソート結果・サイクル検出・グラフ変換
Constants：期待値チェック
Errors：FastAPI の例外ハンドラ 400 / 422 動作
すべて通過すればユーティリティ層の API／ロジック／例外連携が本番相当で正常に機能していることを保証できます。

これで 「共通知識・補助ロジック」 を１か所にまとめ、
上位レイヤー（presence、storage、transport など）から重複なしに呼び出せる“中核ユーティリティ”が完成です。


# test
まずは、下記を行う。
pip install asgi-lifespan httpx
そして、
pytest -v test_utils.py
が全項目パスします。

errors.py のカスタム例外
constants.py の定数
tx_types.py, dag_utils.py の機能
HTTP API でのエンドポイント化
テストによる包括的な検証
がそろい、本番運用可能な状態になります。
