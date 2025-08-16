１. .proto ファイルの配置
city_chain_project/
└── network/
    └── DAGs/
        └── common/
            └── grpc_dag/
                ├── proto/
                │   └── dag.proto         # 既存の dag.proto を移動
                └── gen/                  # ここに Python 用生成コードを出力
                
grpc_dag/proto/*.proto
Python⇔Rust で共有する RPC 定義。たとえば DAGService, StorageService, PoHService などをここにまとめます。

grpc_dag/gen/
python -m grpc_tools.protoc -I. --python_out=gen --grpc_python_out=gen proto/*.proto で生成される Python モジュール群を置くディレクトリ。

５. 呼び出しフロー
Python アプリ が grpc_bridge.client.dag_client.DAGClient で Rust サーバー（grpc_bridge の Tonic 実装）へリクエスト。

Rust サーバー が受け取って高速に処理（PoH 集約、DAG 更新など）し、レスポンス。

必要なら Rust 側も grpc_bridge.client（Rust の client.rs）を使って Python 側の RPC を呼出せる双方向通信も可能。

まとめ
共通 .proto を common/grpc_bridge/proto/ に集約
Python は common/grpc_bridge/gen/ → client/ / server/
Rust は rust_sending/grpc_bridge/ → src/ / proto/
Makefile やスクリプトで自動生成
全体で「gRPC ブリッジ」の役割を担うモジュールとして整理
これで Python ⇔ Rust 間を超高速・非同期に、安全に RPC 連携できるアーキテクチャが完成します。



test_grpc.py のテスト実行方法と補足説明を詳しくお伝えします。

# インストール
pip install grpcio grpcio-tools prometheus-client pytest pytest-asyncio

# 2. プロト生成 (proto 変更時のみ)
cd D:\city_chain_project

python -m grpc_tools.protoc ^
  -Inetwork/sending_DAG/python_sending/common/grpc_dag/proto ^
  --python_out=network/sending_DAG/python_sending/common/grpc_dag/gen ^
  --grpc_python_out=network/sending_DAG/python_sending/common/grpc_dag/gen ^
  network/sending_DAG/python_sending/common/grpc_dag/proto/dag.proto


# 3. 環境変数
export PYTHONPATH=$PWD          # Windows: set PYTHONPATH=%cd%
 OpenSSL が無ければ:
 export GRPC_SKIP_TLS_TEST=1

# 4. テストを個別実行
pytest -v common/grpc_dag/tests/test_retry.py
pytest -v common/grpc_dag/tests/test_timeout.py
pytest -v common/grpc_dag/tests/test_tls.py       # OpenSSL がある場合
pytest -v common/grpc_dag/tests/test_concurrency.py
pytest -v common/grpc_dag/tests/test_fuzz.py

# 5. まとめて
pytest -v common/grpc_dag/tests


✅ pytest -v test_grpc.py だけでテストはOKです！
pytest -v test_grpc.py
これだけで完結します。
なぜなら：

✔ test_grpc.py の中で自動的に gRPCサーバーを立ち上げて、停止までしている からです。
@pytest.fixture(scope="module")
def grpc_server():
    servicer = DummyDAGServicer()
    server = grpc.server(...)
    ...
    yield servicer, port
    server.stop(True)
この pytest fixture が、

サーバーをバックグラウンドで立ち上げ、

テスト終了後に自動で停止します。

❌ python app_grpc.py は テストには不要
app_grpc.py は本番用のgRPCクライアントラッパーです。CLI や本番通信のデモには使いますが、pytest によるテストには 使いません。

🧪 テストで確認できること
✅ gRPC 経由で送信が行えるか (SubmitTransaction)

✅ 通信失敗時にリトライ処理が正しく動作するか

✅ ステータス問い合わせが動作するか (QueryTransactionStatus)

✅ gRPCサーバーとクライアント間の直通が機能するか

# 🔄 応用：他のgRPC実装と統合する場合
たとえば、
sending_DAG/python_sending/city_level/ 側と本当に接続したい場合
サーバーとして grpc_server.py を立ち上げたい場合
そのときは：
# ターミナルA
python grpc_server.py

# ターミナルB（別窓）
python grpc_client.py --endpoint localhost:50051 submit --tx-id tx123 --payload "demo"

✅ 結論
方法	説明
pytest -v	自動サーバー起動あり。開発・単体テスト向け
python grpc_*.py	サーバー／クライアントの手動確認向け

したがって、「pytestだけでいいか？」の答えは「YES」です。
本番統合試験に移るときだけ、grpc_server.py を起動しましょう。


#  すべてのテストが通った＝gRPC レイヤが“基盤”として完成
テスト	何を検証したか	いま通った＝何が保証されたか
test_retry.py	一時的に失敗した RPC が指数バックオフ付きで再送される	retry デコレータが期待どおり動き、ネットワーク瞬断・Leader 切替などに耐える
test_timeout.py	サーバ側の遅延でクライアントがタイムアウトする	デフォルト・デッドラインや StatusCode.DEADLINE_EXCEEDED の扱いが正しい
test_concurrency.py	100 並列送信でロスしないか	サーバ ThreadPool・クライアント Channel が飽和せずスループットを維持
test_fuzz.py	1 byte〜8 kB のランダム・ペイロードを 200 回送信	Payload サイズや文字化けでクラッシュしない (バイト列⇔UTF-8 変換など健全)
test_tls.py	自己署名証明書で mTLS ハンドシェイクして RPC	ChannelFactory の TLS ハンドリング／CN 検証が仕様どおり

いま出来あがっているもの
1) 共通 gRPC パッケージ (common/grpc_dag)
proto/             … dag.proto (IDL)
gen/               … protoc 自動生成コード
client/
    channel.py     … secure/insecure チャンネル生成
    retry.py       … 汎用リトライ・デコレータ
    dag_client.py  … 高レベル API（Submit / Status）
server/
    interceptors.py… Logging・Auth・Exception・Prometheus
    servicer.py    … DAGService 実装ひな型
tests/             … 全 5 種のユニットテスト

ここまでで出来上がった「共通層」の整理
区分、	モジュール、	役割、	依存ポイント
DB、	async_client.py / sync_client.py、	Motor/PyMongo をラップした遅延接続クライアント（CRUD・コンテキスト対応）、	MongoDB URI・DB 名
gRPC クライアント、	client/channel.py、	keep-alive／(m)TLS 付き Channel 生成、	gRPC
　　　　　　　　　  client/retry.py、	指数バックオフ付きリトライ・デコレータ、	time, grpc
                   client/dag_client.py、	DAGServiceStub の高レベル API (submit/query)、	ChannelFactory・retry
gRPC サーバ、	server/servicer.py、	DAGService 実装を DI でラップして起動、	送信側ハンドラ
　　　　　　　　server/interceptors.py、	Logging / Auth / Exception / Metrics、	Prometheus (任意)
Proto、	　　　　proto/dag.proto →　dag_pb2*_auto、	TxRequest/Response, StatusRequest/Response, 　　　　　　　　DAGService、	protoc で自動生成

2) 機能面で揃ったポイント
項目	実装状況	備考
TLS / mTLS	✔︎	ChannelFactory と AuthInterceptor で CN 検証 or メタデータ Token
Keep-Alive & 健康性	✔︎	クライアント／サーバ両方で grpc.keepalive_* オプション
指数バックオフ再試行	✔︎	ステータスコードを限定 (UNAVAILABLE, DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED)
集中ロギング	✔︎	Interceptor で peer・メソッド・レイテンシを INFO 出力
障害マスキング	✔︎	ExceptionInterceptor がスタックトレースを隠蔽し INTERNAL にマッピング
Prometheus メトリクス	✔︎ (import があれば)	RPC カウント & ヒストグラム
負荷試験レベルの同時接続	✔︎	100 並列送信テストにパス
Fuzz / 大量ペイロード	✔︎	8 kB ランダムデータでも OK

# まだ残っている主な TODO
優先	やること	説明
★★★	ロードバランサ (xDS, pick_first→round_robin)	ChannelFactory.create_channel() を拡張し、複数エンドポイント / SRV レコード / Consul などに対応
★★	AuthInterceptor の実運用ロジック	まだ “CN が node- なら OK／token がセットなら OK” の簡易判定。実際には JWT・mTLS 双方向検証を統合する
★★	本番証明書／秘密鍵の管理	k8s Secret か HashiCorp Vault へ。テストは自己署名で代替
★	サーバ graceful-shutdown	kill シグナル → 新規受付停止 → in-flight 完了待ち → 終了
★	Streaming RPC / バイダクション	今は unary-unary のみ定義。必要なら stream メソッドを追加

“どこまで実装できているか”のまとめ
ネットワーク層 (gRPC) はモジュール化され、Python の他コンポーネントから from grpc_dag.client import DAGClient で即利用可能
→ 署名付きトランザクションを送るだけならすぐ組み込める。

再送・TLS・簡易認証・メトリクス を備え“本番運用の最小セット”はクリア。
（＝通信ロスを極小化するという最初のゴールは達成）

以降は ビジネスロジック側 (DAG の検証・永続化・MongoDB 連携) と 厳格なセキュリティ運用 (鍵管理 / 多段認証) を噛み合わせていくフェーズ。

次のステップ提案
DAG 処理 (Rust/Python) と gRPC サーバをワイヤリング
server/servicer.py の CityDAGHandler 呼び出しを実装し、実トランザクションが MongoDB に届くところまで E2E をつなぐ。

k8s / docker-compose で多ノード環境を構築し、Fail-Over テスト
ChannelFactory のロードバランシングを試す。

Secrets 管理 & mTLS 本番証明書
Vault ➜ Envoy SDS などと連携して証明書ローテーションを自動化。

CI パイプラインに gRPC テストを統合
pytest -m "not tls" と自己署名 TLS の両方を GitHub Actions で回す。

これで 「通信ロスを絶対に出したくない最重要レイヤ」 が骨格として出来上がり、上位モジュールを安心して乗せられる状態になりました。

