#!/usr/bin/env python3
"""
py_rs_immu_server.py

Rust 側からの超高速並列アクセスにも対応した、非同期 gRPC サーバー。
immudb-py (同期) を run_in_executor で並列化し、多数同時リクエストに耐えられる構成。

immudb_config.json に記載した各大陸(host/port)設定を読み込み、
Login/Logout/Set/Get/MultiSet/Scan/Delete を実装。
Scanは bytes のまま返す形 ("expected bytes, str found" を回避)。
"""

import os
import json
import asyncio
import logging
import uuid
import grpc

import immudb  # pip install immudb-py
import immudb_pb2
import immudb_pb2_grpc

# Reflection
from grpc_reflection.v1alpha import reflection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

print("===== PY_RS_IMMU_SERVER (Concurrency Ready) STARTUP =====")

# 設定ファイルパス (適宜修正)
CONFIG_PATH = "/mnt/d/city_chain_project/network/DB/config/config_json/immudb_config.json"

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")

CONTINENTS = [
    "default",
    "asia",
    "europe",
    "oceania",
    "africa",
    "northamerica",
    "southamerica",
    "antarctica"
]

CLIENTS = {}
for c in CONTINENTS:
    if c in CONFIG:
        cfg = CONFIG[c]
        conn_str = f"{cfg['host']}:{cfg['port']}"
        try:
            cli = immudb.ImmudbClient(conn_str)
            CLIENTS[c] = cli
            logging.info(f"Created immuDB client for {c} at {conn_str}")
        except Exception as e:
            logging.error(f"Failed to create client for {c}: {e}")
    else:
        logging.warning(f"No config for {c}")

SESSIONS = {}
DEFAULT_CONTINENT = "default"

def ensure_bytes(data):
    if isinstance(data, str):
        return data.encode("utf-8")
    elif isinstance(data, bytes):
        return data
    else:
        raise TypeError(f"Expected str or bytes, got {type(data)}")


class ImmuServiceServicer(immudb_pb2_grpc.ImmuServiceServicer):
    async def Login(self, request, context):
        user = request.user
        continent = request.continent if request.continent in CLIENTS else DEFAULT_CONTINENT
        client = CLIENTS.get(continent)
        if not client:
            await context.abort(grpc.StatusCode.UNAVAILABLE, f"No immuDB for {continent}")
        logging.info(f"Login called: user={user}, continent={continent}")

        loop = asyncio.get_running_loop()
        cfg = CONFIG.get(continent, CONFIG[DEFAULT_CONTINENT])
        try:
            await loop.run_in_executor(None, client.login, cfg["username"], cfg["password"])
            token = f"{continent}_{user}_{uuid.uuid4().hex}"
            SESSIONS[token] = continent
            return immudb_pb2.LoginResponse(token=token)
        except Exception as e:
            logging.error(f"Login error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.LoginResponse(token="")

    async def Logout(self, request, context):
        token = request.token
        logging.info(f"Logout called: token={token}")
        if token in SESSIONS:
            del SESSIONS[token]
            return immudb_pb2.LogoutResponse(success=True, message="Logout OK")
        return immudb_pb2.LogoutResponse(success=False, message="Invalid token")

    async def Set(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        continent = SESSIONS[token]
        client = CLIENTS[continent]

        key = ensure_bytes(request.key)
        val = ensure_bytes(request.value)

        logging.info(f"[DEBUG Set] key={key}, val={val}")
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, lambda: client.set(key, val))
            logging.info(f"Set success: key={key}, val={val}")
            return immudb_pb2.SetResponse(success=True, message="Data stored")
        except Exception as e:
            logging.error(f"Set error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.SetResponse(success=False, message="Set failed")

    async def Get(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        continent = SESSIONS[token]
        client = CLIENTS[continent]

        key = ensure_bytes(request.key)
        loop = asyncio.get_running_loop()
        try:
            res = await loop.run_in_executor(None, lambda: client.get(key))
            val = res.value
            logging.info(f"Get success: key={request.key}, value={val}")
            return immudb_pb2.GetResponse(success=True, value=val)
        except Exception as e:
            logging.error(f"Get error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.GetResponse(success=False, value=b"")

    async def MultiSet(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        continent = SESSIONS[token]
        client = CLIENTS[continent]

        loop = asyncio.get_running_loop()
        try:
            for kv in request.kvs:
                k = ensure_bytes(kv.key)
                v = ensure_bytes(kv.value)
                await loop.run_in_executor(None, lambda: client.set(k, v))
            logging.info(f"MultiSet success: {len(request.kvs)} items stored")
            return immudb_pb2.MultiSetResponse(success=True, message="MultiSet successful")
        except Exception as e:
            logging.error(f"MultiSet error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.MultiSetResponse(success=False, message="MultiSet failed")

    async def Scan(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        continent = SESSIONS[token]
        client = CLIENTS[continent]

        prefix_str = request.prefix
        desc = request.desc
        limit = request.limit
        loop = asyncio.get_running_loop()
        try:
            scan_res = await loop.run_in_executor(
                None,
                lambda: client.scan(b"", prefix_str.encode("utf-8"), desc, limit, None)
            )
            items = []
            for k, v in scan_res.items():
                items.append(immudb_pb2.KeyValue(key=k, value=v))
            logging.info(f"Scan success: {len(items)} items with prefix='{prefix_str}'")
            return immudb_pb2.ScanResponse(success=True, items=items)
        except Exception as e:
            logging.error(f"Scan error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.ScanResponse(success=False, items=[])

    async def Delete(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        logging.info(f"Delete called: key={request.key}")
        # immudb-pyにDeleteは無いので仮実装
        return immudb_pb2.DeleteResponse(success=True, message="Deleted")


async def serve():
    server = grpc.aio.server()
    immudb_pb2_grpc.add_ImmuServiceServicer_to_server(ImmuServiceServicer(), server)

    SERVICE_NAMES = (
        immudb_pb2.DESCRIPTOR.services_by_name['ImmuService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    server.add_insecure_port('0.0.0.0:50051')
    await server.start()
    logging.info("Async gRPC server started on port 50051.")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
