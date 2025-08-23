city_chain_project/network/sending_DAG/python_sending
├── common
│   ├── dist_storage   # storege関連フォルダー
│   ├── grpc_dag
│       ├── client     # channel.py,retry.py,dag_client.pyなどが入っているフォルダー
│       ├── gen        # dag_pb2.pyなどが入っているフォルダー
│       ├── proto      # ntru関連が入っているフォルダー
│       ├── server     # app_grpc.py,interceptors.py,servicer.py等が入っているフォルダー
│       └── tests      # テスト関連が入っているフォルダー
│   ├── proto
│   └── storage_service  # db.py,db_handler.py,node_registry.pyなどが入っているフォルダー
├── core               # core関連フォルダー
├── sender             # sender関連フォルダー
├── storage
│   └── outgoing_dag
├── Tx_flag
│   ├── flag_router
│   └── flag_types
└──  tests

├── db_handler.py                  # MongoDBへの接続・保存処理（受信完了Tx用）
├── distributed_storage_system.py  # 独自分散ストレージシステム（外部保存：ここではファイル出力でシミュレーション）
├── grpc_server.py                 # 各保存ノードのgRPCサーバー（各ノードが常時オンライン）
├── grpc_client.py                 # gRPCクライアント（他ノードへのデータ送信）
├── consensus/
│   ├── __init__.py
│   └── distributed_storage.py     # Narwhal/Tusk＋Mysticetiファストパス方式による分散保存アルゴリズム
├── dag/
│   ├── __init__.py
│   ├── dag_storage.py             # ローカルDAG（未完・完了Txのキャッシュ）管理
│   ├── dag_handler.py             # トランザクション登録と1秒保持後のバッチ処理（送信側・受信側別）
│   ├── dag_utils.py               # ヘルパー関数（ハッシュ計算等）
│   └── dag_anchor.py              # （任意）アンカー管理
├── reward_system.py               # ノード報酬システム（Harmony Token支払いシミュレーション）
└── main.py                        # Flask APIエントリーポイント（送信・受信トランザクション受付）



# モジュール開発のロードマップを詳細にご提案します。

まず、私の理解を確認させてください
・送信フロー
あるノード（送信者）がトランザクションを発行
同時に、受信者の大陸にある gRPC/DAG ハンドラーに流し、DAG へキューイング
さらに、受信者大陸の MongoDB クラスターへ保存フラグを付与し、分散ストレージロジックへフェーズ移行

・分散保存フロー
フラグ付けモジュールで「今すぐ書くべきか」「遅延すべきか」などの判定
優先順位モジュールで「どのライトノードへ書き込むか」を 0–9 スコアと複数因子でソート
最終的にライトノードへ非同期に書込み、ヘッドノードにも別途書込み

パフォーマンス要件
エンドツーエンドで 500ms 未満で完了
各ステップ（DAG 登録、フラグ付与、分散保存）のレイテンシを最小化

暗号化要件
NTRU-KEM で「マスターキー」をカプセル化
MongoDB CSFLE 用マスターキーとして使う
書込時にカプセルを KeyVault へ置き、ガード

拡張性要件
フラグ付け・優先順位付け・分散ルールはそれぞれプラグイン化
将来アルゴリズムを入れ替え可能

改めての進め方（開発ロードマップ）
ステップ 1: アーキテクチャ図と主要コンポーネント定義
エンドツーエンドのシーケンス図
HTTP→DAG→フラグ→優先→MongoDB の流れを視覚化

コンポーネント一覧
SenderAPI（Flask+DAGクライアント）
CityDAGHandler（非同期キューイング）
FlaggingEngine（プラグイン可能なフラグ付け）
PriorityEngine（プラグイン可能なノード選択）
DistributeWorker（非同期保存ワーカー）
MongoCSFLEModule（NTRUカプセル→データキー）

ステップ 2: インターフェース定義
FlaggingEngine
class FlaggingEngine:
    def compute_flag(self, tx_id: str, context: dict) -> int: ...
PriorityEngine

class PriorityEngine:
    def select_nodes(self, flag: int, context: dict) -> list[NodeInfo]: ...
DistributeWorker

class DistributeWorker:
    async def save(self, node: NodeInfo, blob: dict): ...

ステップ 3: モジュール雛形を作成
common/flagging_engine.py
common/priority_engine.py
workers/distribute_worker.py
security/ntru_keywrap.py（NTRUカプセルのラッピング・アンラップ）
integrations/mongo_csfle.py
dag/city_dag_handler.py（既存のCityDAGHandler拡張）

ステップ 4: 各モジュールの “骨格” コードを書き、一つずつユニットテストを通す
FlaggingEngine: テスト用に固定レスポンスを返すスタブから。
PriorityEngine: テスト用にダミーノードリストでソート検証。
DistributeWorker: モックMongoClientに対して非同期 save を呼ぶテスト。
NTRUラッパー: wrap_key/unwrap_key の単体テスト。
MongoCSFLE: 暗号化→復号の round-trip テスト。
CityDAGHandler: キュー注入とコールバックのシミュレーションテスト。

ステップ 5: 組み合わせテスト（結合テスト）
本番環境相当の Docker Compose 上に MongoDB クラスターと簡易 gRPC サーバを起動
SenderAPI からエンドポイントを叩いて一連の保存フローが 500ms 未満で完了することを計測

ステップ 6: 本番運用準備
Kubernetes Helm Chart or ECS 定義ファイル
モニタリング（Prometheus + Grafana）、アラート
リリース手順・ロールバック手順ドキュメント

このロードマップに沿っていかがでしょうか？
具体的なファイル／関数のコードベースでの雛形が必要でしたら、どのコンポーネントから着手されたいかお知らせください。 そこから詳細実装例をお示しします。
