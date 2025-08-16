以下は Observability（分散トレーシング＋メトリクス＋エクスポータ一式） を
共通ライブラリ化した完成版です。

すべて network/DAGs/common/observability/ に配置してください。
common/observability/
├── __init__.py        # パブリック API
├── config.py          # 環境変数集中
├── tracing.py         # OpenTelemetry 初期化／ヘルパ
├── metrics.py         # Prometheus Counter / Histogram 公開
├── exporters.py       # OTLP + Prometheus エクスポータ実装
└── middleware.py      # FastAPI / gRPC 用計測ミドルウェア

依存パッケージ こちらを先にインストールしてください。
pip install opentelemetry-api opentelemetry-sdk
pip install opentelemetry-exporter-otlp opentelemetry-instrumentation-asgi prometheus-client


4. テレメトリ & トレーシング
OpenTelemetry で RPC → PoH → Mongo 書き込み の分散トレース
Prometheus メトリクス：
PoH_REQUEST 発行数／PoH_ACK 受信数
保存完了レイテンシ分布
Presence 呼び出し成功率

5．Observability
Prometheus Interceptor + MongoDB メトリクスコレクタで「Tx/s」「承認遅延」グラフを可視化。Grafana ダッシュボード例を ./docs/observability/ に置いておくと運用が楽。

これはどのフォルダー構成とファイル構成になる？ファイル名とコードも記載して

ChatGPT said:
以下のように「観測／可観測性（Observability）」まわりのコードを network/DAGs/common/observability/ 配下にまとめるのがベストです。

network/DAGs/common/observability/
├── __init__.py
├── config.py
├── tracing.py
├── metrics.py
└── exporters.py


使い方例：

# grpc_server.py で PoH_REQUEST 発行後
from network.DAGs.common.observability.metrics import record_poh_request
record_poh_request(region="Asia")

# grpc_client.py で PoH_ACK 受信
from network.DAGs.common.observability.metrics import record_poh_ack
record_poh_ack(region="Asia")

# Storage 完了時
from network.DAGs.common.observability.metrics import record_storage_latency
start = time.time()
# ... 保存処理 ...
record_storage_latency(time.time() - start)

# Presence 呼び出し時
from network.DAGs.common.observability.metrics import record_presence
try:
    nodes = await get_online_nodes(region)
    record_presence(True, region)
except:
    record_presence(False, region)

以上を組み込むことで、
分散トレース：RPC→PoH→DB 書き込みの一連を OpenTelemetry で可視化
メトリクス：Prometheus に PoH 発行数／受信数、レイテンシ、Presence 成功率を出力
が、きれいに common/observability/ 配下にまとまります。これで「どこで・何が・どれだけ」起きているか、リアルタイムにモニタリング＆トレース可能になります。


7. 使い方（sending_DAG 例）
from common.observability import init_observability
from fastapi import FastAPI
from common.observability.middleware import ObservabilityMiddleware, OpenTelemetryMiddleware

init_observability("sending-dag")  # ← 必ず最初に

app = FastAPI()
app.add_middleware(OpenTelemetryMiddleware)  # トレース自動付与
app.add_middleware(ObservabilityMiddleware)  # メトリクス＋span補強

gRPC サーバ
from common.observability import init_observability
from common.observability.middleware import GRPCObservabilityInterceptor

init_observability("grpc-dag")
server = grpc.server(..., interceptors=[GRPCObservabilityInterceptor()])
Mongo コレクタ は init_exporters() 内登録だけで自動動作
（pymongo が global monitoring API を呼びます）。

8. Grafana ダッシュボード例
./docs/observability/ に下記 JSON を置くとすぐ読み込めます：
docs/observability/
└── grafana_dash.json   <- Tx/s, PoH lat, Presence success などを可視化

まとめ
Tracing：init_tracer_provider() が OTLP gRPC へ自動エクスポート
Metrics：init_metrics() が 0.0.0.0:8000/metrics で Prometheus scrape
MongoDB latency, gRPC latency, HTTP レイテンシ を標準化
ObservabilityMiddleware / GRPCObservabilityInterceptor を組み込むだけで
アプリ全体の計測が完了

これで 「RPC → PoH → Mongo 書き込み」 の分散トレースと
Prometheus による Tx/s・承認遅延・Presence 成功率 の可視化が
一気通貫で行える環境が整いました。


# 📡 Observability サブシステム ― 機能の全体像
レイヤー	ファイル	役割
トレース	tracing.py	OpenTelemetry SDK を初期化し、OTLP gRPC へ span をストリーミング
メトリクス	metrics.py	Prometheus Counter / Histogram を定義し、start_http_server() で /metrics を公開
Mongo 監視	exporters.py	PyMongo のコマンドイベントをフックし、書込レイテンシを Histogram へ記録
ASGI / gRPC ミドルウェア	middleware.py	ルート span 付与＋単リクエスト Counter 増分・レイテンシ測定
デモ & 実行	app_observability.py	上記を組み込んだ FastAPI サンプル (/ping, /poh)
E2E テスト	test_observability.py	In-memory exporter と Prometheus のテキスト出力で機能検証

主な観測ポイント
メトリクス名	説明
poh_requests_total{endpoint, status}	ルートごとのリクエスト数
poh_ack_total{endpoint}	/poh エンドポイントが ACK を返した回数
storage_latency_seconds	MongoDB 書込レイテンシ
grpc_method_latency_seconds	gRPC サーバー側のメソッドレイテンシ

トレースは service.name = observ-demo として OTLP Collector に送信。
（Collector が無ければ再試行ログが出るだけでアプリ動作へ影響なし）

🔬 データフロー
sequenceDiagram
    participant Client
    participant FastAPI as FastAPI (OpenTelemetry ASGI)
    participant OTelMW as ObservabilityMiddleware
    participant Business as /poh Handler
    participant Prom as prometheus_client
    participant OTLP as OTLP Exporter

    Client->>FastAPI: HTTP /poh POST
    FastAPI->>OTelMW: span(/poh)
    OTelMW->>Business: call
    activate Business
    Business->>Prom: Counter.inc (REQUEST) & _do_work()
    Business-->>OTelMW: return 200
    deactivate Business
    OTelMW->>Prom: Counter.inc (ACK) & Histogram.observe(lat)
    OTelMW-->>Client: JSON {"ack":true}
    OTelMW->>OTLP: export span

🚀 使い方ガイド
1. サーバを起動してみる
# プロジェクト直下
python -m network.DAGs.common.observability.app_observability
# → http://localhost:8081/ping  (動作確認)
# → http://localhost:8000/metrics (Prometheus scrape)
環境変数
OTLP_GRPC_ENDPOINT … Collector の gRPC アドレス (既定: localhost:4317)
PROMETHEUS_BIND … /metrics 待受 (既定: 0.0.0.0:8000)

2. 既存 FastAPI アプリへ組込む
from fastapi import FastAPI
from common.observability.tracing import init_tracer_provider
from common.observability.metrics import init_metrics
from common.observability.exporters import init_exporters
from common.observability.middleware import ObservabilityMiddleware
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

# 初期化を一度だけ
init_tracer_provider("sending-dag")
init_metrics()
init_exporters("sending-dag")

app = FastAPI()
app.add_middleware(OpenTelemetryMiddleware)   # span 自動付与
app.add_middleware(ObservabilityMiddleware)   # Counter + Latency

3. gRPC サーバーへ組込む
import grpc
from concurrent import futures
from common.observability.tracing import init_tracer_provider, init_metrics, init_exporters
from common.observability.middleware import GRPCObservabilityInterceptor

init_tracer_provider("grpc-dag")
init_metrics(); init_exporters("grpc-dag")

server = grpc.server(
    futures.ThreadPoolExecutor(max_workers=10),
    interceptors=[GRPCObservabilityInterceptor()],
)

4. Grafana ダッシュボード
docs/observability/grafana_dash.json を Grafana にインポートすると
以下の図がすぐ使えます：
Tx/s
PoH_ACK 数
保存レイテンシ p50 / p90
Presence 成功率

🧪 テストの考え方
InMemorySpanExporter … Collector 不在でも span を取得
prometheus_client.generate_latest() … /metrics HTTP を通さず
その場でテキストを取得

テストでは
ルート span が 5 つ以上存在する
/ping /poh のカウンタ値が期待以上
をチェックし、OpenTelemetry バージョン差異に強くしました。

まとめ
init_tracer_provider × init_metrics × ミドルウェア だけで
トレース と メトリクス を自動組込。
MongoDB 書込レイテンシや gRPC も exporters / interceptors で統一計測。
Prometheus と OTLP Collector があれば即座に Grafana 可視化。
Collector が無くてもアプリ自体は問題なく動作。
test_observability.py が E2E で品質担保し、将来のバージョン変動へも対応可能。

これで 送信 DAG → PoH → ストレージ の一連フローを
“数値でも軌跡でも” 追いかけられる環境が完成しました。
