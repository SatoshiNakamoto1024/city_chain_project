common/grpc_dag/
├── proto/
│   └── dag.proto
├── gen/                 # 自動生成コードのみ
│   ├── __init__.py
│   ├── dag_pb2.py
│   └── dag_pb2_grpc.py
├── client/
│   ├── __init__.py
│   ├── channel.py       # ChannelFactory, LB, mTLS, keep-alive
│   ├── retry.py         # 共通リトライ／バックオフロジック
│   └── dag_client.py    # 高レベル API (今の GRPCClient をここへ)
├── server/
│   ├── __init__.py
│   ├── interceptors.py  # 認証, ロギング, リカバリ, Prometheus
│   ├── servicer.py      # 今の *ServicerImpl
│   └── app.py           # 起動スクリプト (今の grpc_server.py)
└── tests/
    ├── test_retry.py
    ├── test_timeout.py
    ├── test_tls.py
    ├── test_concurrency.py
    └── test_fuzz.py


2. クライアント側 拡張ポイント
機能	追加/変更	実装イメージ
mTLS	＋	channel.py で grpc.ssl_channel_credentials(cert_chain, private_key, root_ca) を組み立て、クライアント証明書を読み込む。
サーキットブレーカ	＋	retry.py に pybreaker（または自前実装）を組み込む。連続失敗でオープン→一定時間後にハーフオープン。
自動 Channel 再生成	修	GRPCClient に “疎通ヘルスチェック + 失敗閾値” で channel を再ビルドするロジックを追加。
メトリクス	＋	prometheus_client で request_total / latency_ms / retry_count / circuit_break_open_total を Export。
Deadline Propagation	＋	Application 上位からの timeout を gRPC Metadata に入れて多段伝搬。
名前解決と LB	＋	DNS ラウンドロビン or xDS API サポート (grpclb / pick_first) を ChannelFactory に実装。

3. サーバ側 拡張ポイント
機能	追加/変更	実装イメージ
双方向 mTLS	＋	server.app で grpc.ssl_server_credentials([(priv_key, cert_chain)], root_ca, True) を渡す。
AuthZ インターセプタ	＋	JWT / API-Key / 署名検証を行う AuthInterceptor を interceptors.py で定義。
Recovery インターセプタ	＋	例外を catch し StatusCode.INTERNAL で返す。
Streaming 対応	＋	SubmitTransactionStream を追加。大量 Tx を１ストリームで送る → RTT 削減。
Flow Control	＋	受信キューが飽和したら RESOURCE_EXHAUSTED を返しクライアントに Back-Pressure。
ヘルスチェック & リフレクション	＋	grpc_health.v1 & grpc_reflection.v1alpha を登録 → k8s や LB が活用。
Graceful Shutdown	修	SIGTERM/SIGINT で in-flight RPC を待ってから server.stop(grace=True)。

4. テスト拡充プラン
テスト名	目的	手法
test_retry.py	リトライ／バックオフが正しく発火するか	Dummy サーバーで 2回 UNAVAILABLE→成功
test_timeout.py	Deadline 超過時に DEADLINE_EXCEEDED が返るか	サーバー側でわざと sleep
test_tls.py	mTLS ハンドシェイク成功／失敗パターン	trustme で自己署名 CA を生成
test_concurrency.py	1000 並列送信でロストなし	pytest-xdist + ストリーム RPC
test_fuzz.py	Fuzzing でシリアライズ例外が起きないか	python-fuzz でランダム payload
Chaos テスト	パケットロス・遅延でも再送できるか	toxiproxy or tc netem で 5–30% loss 注入
Long-running soak	24h 連続送信でメモリリークがないか	pytest-benchmark + Prometheus
Proto互換テスト	新旧クライアント/サーバの互換性	GitHub Actions で前バージョン artefact と交差テスト

すべて pytest で走るようにし、CI 失敗＝デプロイ不可とする。
