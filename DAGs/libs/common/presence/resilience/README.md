下記のように、network/DAGs/common/presence/ 配下に「レジリエンス／耐障害性」を担う新しいサブフォルダを作り、そこにサーキットブレーカーとレートリミッターを収めます。

network/DAGs/common/presence/
├── __init__.py
├── client.py
├── server.py
├── test_presence.py
└── resilience/
    ├── __init__.py
    ├── circuit_breaker.py
    ├── rate_limiter.py
    ├── app_resilience.py   ← ★ 新規
    └── test_resilience.py  ← ★ 新規

# test
pip install -U "httpx>=0.27"
を事前にやっておくこと。

client.py での組み込み例
# network/DAGs/common/presence/client.py

import asyncio
import httpx
from .resilience.circuit_breaker import CircuitBreaker
from .resilience.rate_limiter import TokenBucket
from .resilience.errors import CircuitOpenError, RateLimitExceeded

# Presence Service への呼び出しは秒間 100 req、瞬間バーストは 200 req まで許容
rate_limiter = TokenBucket(rate=100.0, capacity=200)
# 3 回失敗で OPEN、30秒後に HALF_OPEN に移行
circuit_breaker = CircuitBreaker(fail_max=3, reset_timeout=30.0)

async def get_online_nodes(region: str) -> list[str]:
    url = f"https://presence.service/presence?region={region}"
    try:
        # レート制限
        rate_limiter.acquire()
        # サーキットブレーカー
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: circuit_breaker.call(httpx.get, url, timeout=1.0)
        )
        response.raise_for_status()
        return response.json()
    except (CircuitOpenError, RateLimitExceeded) as e:
        # ログに残す or フォールバック
        print(f"[presence] resilience skip: {e}")
        return []  # Presence情報なしとして扱う
    except Exception as e:
        # その他の通信エラーは上位に伝播
        raise

流れ
rate_limiter.acquire() で秒間レートを超えるアクセスをブロック
circuit_breaker.call() で直近失敗が重なりすぎていれば即座にスキップ
通常どおり HTTP GET → JSON parse
Presence Service がダウンしても短時間で自動的に回復を試みつつ、大量リクエストで自滅しない堅牢性が得られます。
