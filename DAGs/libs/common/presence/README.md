# Presence Service (HTTP API＋キャッシュ)

📦 presence / resilience サブシステム ― 何を担うか
階層	フォルダ	役割	キーコンポーネント
presence	common/presence/	“オンライン中ノード” の 永続管理 API	server.py (FastAPI)、client.py (SDK)、config.py
resilience	common/presence/resilience/	presence だけでなく全ネットワーク共通で使える 耐障害ユーティリティ	circuit_breaker.py、rate_limiter.py、errors.py

1. presence サービスの構造
client.py        : Presence API 呼び出し SDK（aiohttp / httpx どちらでも可）
server.py        : FastAPI + Redis 実装
app_presence.py  : サーバープロセス起動ラッパー
config.py        : すべての環境変数を一括定義
test_presence.py : FakeRedis でフル E2E テスト

サーバ動作フロー
sequenceDiagram
    participant Node as DAG Node
    participant ClientSDK as PresenceClient
    participant PresenceAPI as FastAPI Server
    participant Redis as Redis

    Node->>ClientSDK: login(node_id)
    ClientSDK->>PresenceAPI: POST /presence/login
    PresenceAPI->>Redis: SADD presence:online, SET presence:last_seen
    PresenceAPI-->>ClientSDK: 200 OK

    loop HEARTBEAT_SEC (例 3s)
        Node->>ClientSDK: heartbeat(node_id)
        ClientSDK->>PresenceAPI: POST /presence/heartbeat
        PresenceAPI->>Redis: SET + TTL
    end

    Node->>ClientSDK: list_nodes()
    ClientSDK->>PresenceAPI: GET /presence
    PresenceAPI->>Redis: SMEMBERS + GET
    PresenceAPI-->>ClientSDK: [{"node_id":...}]

Rate-Limiter Middleware — IP 単位で 30req/s バースト60を許可
(config.RATE_LIMIT_*)

Resilience — PresenceClient 側に
CircuitBreaker: list_nodes() の一時障害を自動遮断
RateLimiter: クライアント自体の暴走を抑制

2. resilience ユーティリティ
ファイル	機能
circuit_breaker.py	最大失敗回数・クールダウン秒を指定してデコレータ化
rate_limiter.py	トークンバケット。await limiter.acquire() で消費
errors.py	共通例外 (CircuitOpenError, RateLimitExceeded)
app_resilience.py	デモ用 FastAPI (/unstable, /limited)
test_resilience.py	httpx + monkeypatch で Circuit/Rate 両方を網羅テスト

ポイント：resilience は presence 以外 のレイヤー（gRPC クライアント、外部 API 呼び出し）でもそのまま再利用できます。

3. 使い方ガイド
3-1. サーバを立ち上げる
# 必須：Redis を起動
docker run -d --name redis -p 6379:6379 redis:7

# 任意：環境値をカスタム
export PRESENCE_HTTP_PORT=9000
export PRESENCE_REDIS_URI="redis://localhost:6379/0"

# 起動
python -m network.DAGs.common.presence.app_presence
# → http://localhost:9000/presence

3-2. クライアント SDK を使う（どこからでも）
import asyncio
from common.presence import PresenceClient

async def main():
    pc = PresenceClient("http://localhost:9000/presence")

    await pc.login("node-123")            # 参加宣言
    await pc.heartbeat("node-123")        # 3 秒感覚で呼ぶ
    nodes = await pc.list_nodes()         # 現在のオンラインリスト
    print([n.node_id for n in nodes])

    await pc.logout("node-123")           # 離脱

asyncio.run(main())
自前の httpx.AsyncClient を渡したい場合
import httpx, asyncio
from common.presence import PresenceClient
from httpx import ASGITransport
from common.presence.server import create_app  # ローカル ASGI テスト例

client = httpx.AsyncClient(
    transport=ASGITransport(app=create_app(), lifespan="off"),
    base_url="http://test"
)
pc = PresenceClient("http://test/presence", session=client)

3-3. CircuitBreaker / RateLimiter を独立利用
from common.presence.resilience import circuit_breaker, RateLimiter

@circuit_breaker(max_failures=4, reset_timeout=5)
async def call_remote():
    ...

limiter = RateLimiter(rate=5, capacity=10)

async def guarded():
    await limiter.acquire()
    await call_remote()

4. 環境変数早見表（presence/config.py）
変数	既定	説明
NODE_ID	<hostname>	PresenceClient のデフォルト node_id
PRESENCE_REDIS_URI	redis://localhost:6379/0	Redis エンドポイント
PRESENCE_HTTP_PORT	8080	FastAPI サーバポート
PRESENCE_HEARTBEAT_SEC	3	Heartbeat 間隔
PRESENCE_RATE_LIMIT_RATE	30	サーバミドルウェア: 補充レート (req/s)
PRESENCE_RATE_LIMIT_CAPACITY	60	同: バースト上限

5. テスト戦略
unit
test_resilience.py：CircuitOpen / RateExceeded を確 deterministically 検証
レガシー httpx 0.25–0.28 まで動的対応

integ (Presence)
test_presence.py：FakeRedis 注入 → login / list / heartbeat / logout を往復
PresenceClient も httpx セッションでラウンドトリップ
CI では単に
pytest network/DAGs/common/presence -q
を実行すれば Redis 実体不要 で全テストが通ります。

🚀 これでできること
sending_DAG / receiving_DAG から
from common.presence import PresenceClient
nodes = await PresenceClient(...).list_nodes()
と呼ぶだけでオンラインリスト取得（Retry & CB 内蔵）。

フロントAPI や CLI ツール から HP/負荷情報が欲しいときは
REST 呼び出し一つでロード可能。

レジリエンスユーティリティ を
他の外部サービス呼び出しでも再利用し、障害ドメインを局所化。

これで Presence レイヤー＆耐障害ユーティリティ が
本番運用・自動テスト・開発すべてのシーンで一貫して活用できる体制になりました。
