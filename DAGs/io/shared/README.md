下記は “city_chain_project/DAGs” をワークスペースのルートとしたときの
完全版フォルダー構成（Rust + Python 混在、送信 DAG / 受信 DAG / 共通 libs を分離） です。
下表は IO レイヤ（≈130 個想定） の代表フォルダーを
「① sending DAG 専用」「② receiving DAG 専用」「③ 両方で共有」に振り分けたものです。

    ├── io/                             ← **I/O プラグイン (送信専用 / 受信専用 / 共有)**
│   └── shared/                     ← ③ 共有 18 個
    │       ├── io_network_grpc/   (3)
    │       ├── io_network_http/   (3)
    │       ├── io_network_ws/     (3)
    │       ├── io_serialization_cbor/  (2)
    │       ├── io_serialization_flatbuf/ (2)
    │       ├── io_serialization_arrow/ (2)
    │       ├── io_serialization_capnp/ (2)
    │       ├── io_storage_shardmap/ (3)
    │       ├── io_message_grpc_stream/ (3)
    │       ├── io_storage_redis/  (3)
    │       ├── io_tls_rustls/     (2)
    │       ├── io_auth_jwt/       (1)
    │       ├── io_logging_json/   (1)
    │       ├── io_logging_ansi/   (1)
    │       ├── io_metrics_prom/   (1)
    │       ├── io_telemetry_otlp/ (1)
    │       ├── io_pipeline_worker/ (3)
    │       └── io_admin_api/      (3)

③ sending / receiving 両方で共有する I/O フォルダー
フォルダー(スコープ)	役割
io_network_grpc (3)	tonic / aio 双方向ストリーミング
io_network_http (3)	RESTful API（管理/ヘルス）
io_network_ws (3)	WebSocket サブスク（UI ダッシュボード）
io_serialization_cbor (2)	Compact MsgPack 互換
io_serialization_flatbuf (2)	ゼロコピー shard ペイロード
io_serialization_arrow (2)	バッチ分析用 Columnar
io_serialization_capnp (2)	極小ヘッダ RPC
io_storage_shardmap (3)	“どのノードがどの shard” メタ
io_message_grpc_stream (3)	gRPC 内部 Pub/Sub
io_storage_redis (3)	キャッシュ & メタ TTL
io_tls_rustls (2)	mTLS / ALPN 共通
io_auth_jwt (1)	API 認証トークン検証
io_logging_json (1)	構造化ログ出力
io_logging_ansi (1)	CLI-color ログ
io_metrics_prom (1)	Prometheus exporter
io_telemetry_otlp (1)	OpenTelemetry Trace
io_admin_api (3)	/admin/* 共通制御 API
io_pipeline_worker (3)	repair → decode → commit チェーン（受信側でも使用）
