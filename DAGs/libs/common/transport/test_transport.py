# city_chain_project\network\DAGs\common\transport\test_transport.py
# network/DAGs/common/transport/test_transport.py
import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager          # ★ 追加ライブラリ
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from transport.app_transport import app


@pytest.mark.asyncio
async def test_grpc_echo_and_retry():
    # Startup / Shutdown を確実に回す
    async with LifespanManager(app):
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as cli:
            # 1) gRPC Echo
            r = await cli.get("/grpc_echo", params={"payload": "hello-123"})
            assert r.status_code == 200
            assert r.json() == {"echo": "hello-123"}

            # 2) retry 成功
            r2 = await cli.get("/retry_test", params={"failures": 1})
            assert r2.status_code == 200 and r2.json() == {"result": "ok"}

            # 3) retry 上限超え
            r3 = await cli.get("/retry_test", params={"failures": 5})
            assert r3.status_code == 500
