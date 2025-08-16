#!/usr/bin/env python3
"""
py_rs_immu_server.py

このサーバーは、設定ファイル immudb_config.json から各大陸（default, asia, europe, australia, africa, northamerica, southamerica, antarctica）の接続先を読み込み、
それぞれの immuDBクライアント（immudb-py）を生成します。
リクエスト（Login, Logout, Set, Get, MultiSet, Scan, Delete）は、リクエスト内の"continent"フィールドに応じて該当するクライアントへルーティングします。

Reflection も有効にしています。
"""
print("===== PY_RS_IMMU_SERVER - SCAN FIX VERSION - STARTUP =====")

import os
import json
import asyncio
import grpc
import logging
import uuid

import immudb  # pip install immudb-py

import immudb_pb2
import immudb_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 設定ファイルのパス（適宜変更してください）
CONFIG_PATH = "/mnt/d/city_chain_project/network/DB/config/config_json/immudb_config.json"

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")

# 8大陸のリスト
CONTINENTS = [
    "default",
    "asia",
    "europe",
    "australia",
    "africa",
    "northamerica",
    "southamerica",
    "antarctica"
]

CLIENTS = {}
for continent in CONTINENTS:
    if continent in CONFIG:
        cfg = CONFIG[continent]
        conn_str = f"{cfg['host']}:{cfg['port']}"
        try:
            client = immudb.ImmudbClient(conn_str)
            CLIENTS[continent] = client
            logging.info(f"Created immuDB client for {continent} at {conn_str}")
        except Exception as e:
            logging.error(f"Failed to create client for {continent}: {e}")
    else:
        logging.warning(f"No configuration found for {continent}")

# セッション管理
SESSIONS = {}
DEFAULT_CONTINENT = "default"

def ensure_bytes(data):
    """str を bytes に変換し、すでに bytes の場合はそのまま返す"""
    if isinstance(data, str):
        return data.encode("utf-8")
    elif isinstance(data, bytes):
        return data
    else:
        raise TypeError(f"Expected str or bytes, got {type(data)}")


class ImmuServiceServicer(immudb_pb2_grpc.ImmuServiceServicer):
    async def Login(self, request, context):
        try:
            user = request.user
            password = request.password
            # 大陸選択
            continent = request.continent if request.continent in CLIENTS else DEFAULT_CONTINENT
            client = CLIENTS.get(continent)
            if client is None:
                await context.abort(grpc.StatusCode.UNAVAILABLE, f"No immuDB client available for continent: {continent}")
            logging.info(f"Login called: user={user}, continent={continent}")

            loop = asyncio.get_running_loop()
            cfg = CONFIG.get(continent, CONFIG[DEFAULT_CONTINENT])
            await loop.run_in_executor(None, client.login, cfg["username"], cfg["password"])

            token = f"{continent}_{user}_{uuid.uuid4().hex}"
            SESSIONS[token] = continent
            return immudb_pb2.LoginResponse(token=token)
        except Exception as e:
            logging.error(f"Login exception: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.LoginResponse(token="")

    async def Logout(self, request, context):
        token = request.token
        logging.info(f"Logout called: token={token}")
        if token in SESSIONS:
            del SESSIONS[token]
            return immudb_pb2.LogoutResponse(success=True, message="Logout OK")
        else:
            return immudb_pb2.LogoutResponse(success=False, message="Invalid token")

    async def Set(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        continent = SESSIONS[token]
        client = CLIENTS.get(continent)

        key = ensure_bytes(request.key)
        val = ensure_bytes(request.value)

        logging.info(f"[DEBUG Set] key type: {type(key)}, val type: {type(val)}")
        logging.info(f"[DEBUG Set] key = {key}, val = {val}")

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: client.set(key, val))
            logging.info(f"Set success: key={key}, value={val}")
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
        client = CLIENTS.get(continent)

        key = request.key
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, lambda: client.get(key.encode('utf-8')))
            decoded_val = result.value if isinstance(result.value, bytes) else result.value.encode('utf-8')
            logging.info(f"Get success: key={key}, value={decoded_val}")
            return immudb_pb2.GetResponse(success=True, value=decoded_val)
        except Exception as e:
            logging.error(f"Get error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.GetResponse(success=False, value="")

    async def MultiSet(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        continent = SESSIONS[token]
        client = CLIENTS.get(continent)

        try:
            loop = asyncio.get_running_loop()
            for kv in request.kvs:
                # kv.key と kv.value は既に bytes かもしれないが念のため
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
        client = CLIENTS.get(continent)

        prefix_str = request.prefix
        desc = getattr(request, "desc", False)
        limit = getattr(request, "limit", 10)

        try:
            loop = asyncio.get_running_loop()
            # immudb-py: scan(key, prefix, desc, limit, sinceTx=None)
            scan_results_dict = await loop.run_in_executor(
                None,
                lambda: client.scan(
                    b"",  # key: ここでは空から始める
                    prefix_str.encode("utf-8"),
                    desc,
                    limit,
                    None  # sinceTx
                )
            )
            items = []
            # scan_results_dict は Dict[bytes, bytes]
            for k, v in scan_results_dict.items():
                items.append(
                    immudb_pb2.KeyValue(
                        key=k,
                        value=v
                    )
                )

            logging.info(f"Scan success: Found {len(items)} items with prefix '{prefix_str}'")
            return immudb_pb2.ScanResponse(success=True, items=items)
        except Exception as e:
            logging.error(f"Scan error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.ScanResponse(success=False, items=[])

    async def Delete(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        # 省略。ここは未実装でOK
        return immudb_pb2.DeleteResponse(success=True, message="Deleted")


async def serve():
    server = grpc.aio.server()
    immudb_pb2_grpc.add_ImmuServiceServicer_to_server(ImmuServiceServicer(), server)

    from grpc_reflection.v1alpha import reflection
    SERVICE_NAMES = (
        immudb_pb2.DESCRIPTOR.services_by_name['ImmuService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    server.add_insecure_port('0.0.0.0:50051')
    await server.start()
    logging.info("Async gRPC server started on port 50051.")
    await server.wait_for_termination()

if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logging.info("Async gRPC server shutting down.")
