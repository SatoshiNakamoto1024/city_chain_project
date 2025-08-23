# D:\city_chain_project\network\DAGs\common\presence\test_presence.py
"""
test_presence.py
----------------
Presence Server の全ルートを Redis 依存なしでエンドツーエンド検証。
・FakeRedis へ monkeypatch
・httpx (0.25–0.28 互換) で ASGI 経由リクエスト
"""
from __future__ import annotations
import inspect
from typing import Dict, Set
import pytest
import httpx

from . import server as pres_svr


# ─────────────────────────────────────────────
# 1) FakeRedis 実装  (最低限のコマンドのみ)
# ─────────────────────────────────────────────
class FakeRedis:
    def __init__(self):
        self._set: Set[str] = set()
        self._kv: Dict[str, str] = {}

    # ---- pipeline API ----
    class _Pipe:
        def __init__(self, outer: "FakeRedis"):
            self.outer = outer
            self.ops = []

        def sadd(self, key, val):
            self.ops.append(("sadd", key, val)); return self

        def srem(self, key, val):
            self.ops.append(("srem", key, val)); return self

        def set(self, key, val, ex=None):
            self.ops.append(("set", key, val)); return self

        def delete(self, key):
            self.ops.append(("del", key)); return self

        async def execute(self):
            for op in self.ops:
                match op[0]:
                    case "sadd": self.outer._set.add(op[2])
                    case "srem": self.outer._set.discard(op[2])
                    case "set":  self.outer._kv[op[1]] = op[2]
                    case "del":  self.outer._kv.pop(op[1], None)
            self.ops.clear()

    def pipeline(self):
        return FakeRedis._Pipe(self)

    # ---- simple cmds ----
    async def set(self, key, val, ex=None):
        self._kv[key] = val

    async def delete(self, key):
        self._kv.pop(key, None)

    async def smembers(self, key):
        return self._set.copy()

    async def sadd(self, key, val):
        self._set.add(val)

    async def srem(self, key, val):
        self._set.discard(val)

    async def exists(self, key):
        return key in self._kv

    async def get(self, key):
        return self._kv.get(key)

    async def ttl(self, key):
        return 10

    @classmethod
    def from_url(cls, *_a, **_kw):
        return cls()


# ─────────────────────────────────────────────
# 2) monkeypatch Redis before startup
# ─────────────────────────────────────────────
pres_svr.Redis = FakeRedis          # type: ignore[attr-defined]
pres_svr.redis = FakeRedis()        # global instance used later

app = pres_svr.create_app()         # FastAPI app (startup uses FakeRedis)


# ─────────────────────────────────────────────
# 3) httpx バージョン互換クライアント
# ─────────────────────────────────────────────
def get_client() -> httpx.AsyncClient:
    if "app" in inspect.signature(httpx.AsyncClient.__init__).parameters:
        return httpx.AsyncClient(app=app, base_url="http://t")
    # >=0.27 系
    tr_sig = inspect.signature(httpx.ASGITransport.__init__)
    tr = httpx.ASGITransport(app=app, lifespan="off") if "lifespan" in tr_sig.parameters \
         else httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=tr, base_url="http://t")


# ─────────────────────────────────────────────
# 4) テスト本体
# ─────────────────────────────────────────────
@pytest.mark.asyncio
async def test_presence_lifecycle():
    async with get_client() as cli:
        # login
        assert (await cli.post("/presence/login", json={"node_id": "n1"})).status_code == 200
        # list → 1 件
        resp = await cli.get("/presence")
        assert resp.status_code == 200 and len(resp.json()) == 1

        # heartbeat
        assert (await cli.post("/presence/heartbeat", json={"node_id": "n1"})).status_code == 200

        # logout
        assert (await cli.post("/presence/logout", json={"node_id": "n1"})).status_code == 200
        # list → 0 件
        resp = await cli.get("/presence")
        assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_presence_client_wrapper():
    """ PresenceClient 経由で同じフローを確認 """
    from .client import PresenceClient

    pc = PresenceClient("http://t/presence", session=get_client())

    await pc.login("node-X")
    nodes = await pc.list_nodes()
    assert nodes and nodes[0].node_id == "node-X"

    await pc.heartbeat("node-X")
    await pc.logout("node-X")
    nodes = await pc.list_nodes()
    assert not nodes
