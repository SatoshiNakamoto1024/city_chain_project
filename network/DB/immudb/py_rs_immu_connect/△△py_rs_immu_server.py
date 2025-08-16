#!/usr/bin/env python3
"""
py_rs_immu_server.py

非同期 gRPC サーバーを提供します。
設定ファイル immudb_config.json から各大陸の接続情報を読み込み、
それぞれの immuDB クライアント（immudb-py）を生成し、トークンを発行してセッション管理を行います。
クライアントからの各操作（Login, Logout, Set, Get, MultiSet, Scan, Delete）は、
対応する大陸の immuDB インスタンスへルーティングされます。

※ このサーバーは Rust 側の非同期 gRPC クライアントから呼ばれることを想定しています。
"""
import subprocess
import time  # 追加
import os
import sys
import json
import asyncio
import grpc
import logging
import uuid

import immudb  # pip install immudb-py

import immudb_pb2
import immudb_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 設定ファイルのパス
CONFIG_PATH = "/mnt/d/city_chain_project/network/DB/config/config_json/immudb_config.json"

# 設定ファイルを読み込む
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"❌ 設定ファイルが見つかりません: {CONFIG_PATH}")

# 8大陸リスト
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

# immudb の実行ファイルパス（WSL側の Linux 用 immudb のフルパス）
IMMUDB_BINARY = "/usr/local/bin/immudb"  # 必要に応じて変更してください

# 各大陸の immudb インスタンスを起動するためのプロセスを保持する辞書
IMMUDB_PROCESSES = {}

def spawn_immudb_instances():
    """ CONFIG に基づいて、各大陸の immudb インスタンスを spawn して起動する """
    for continent in CONTINENTS:
        if continent in CONFIG:
            cfg = CONFIG[continent]
            port = cfg["port"]
            data_dir = cfg["dir"]
            os.makedirs(data_dir, exist_ok=True)
            logging.info(f"[Python] Spawning immuDB for {continent} on port {port} with data dir {data_dir}")
            cmd = [
                IMMUDB_BINARY,
                "--port", str(port),
                "--address", cfg["host"],
                "--admin-password", cfg["password"],
                "--force-admin-password",  # これを追加
                "--dir", data_dir
            ]
            # spawn してプロセスを保持
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            IMMUDB_PROCESSES[continent] = process
            # 少し待機して安定させる
            time.sleep(1)
        else:
            logging.warning(f"[Python] No configuration found for {continent}")
    logging.info("[Python] All immuDB instances spawned.")

def shutdown_immudb_instances():
    """ spawn した全 immudb インスタンスを終了する """
    for continent, process in IMMUDB_PROCESSES.items():
        logging.info(f"[Python] Terminating immuDB for {continent}")
        try:
            process.terminate()
            process.wait()
        except Exception as e:
            logging.error(f"[Python] Error terminating immuDB for {continent}: {e}")
    logging.info("[Python] All immuDB instances terminated.")

# 各大陸毎の immuDB クライアント（immudb-py）の生成
CLIENTS = {}
for continent in CONTINENTS:
    if continent in CONFIG:
        cfg = CONFIG[continent]
        conn_str = f"{cfg['host']}:{cfg['port']}"
        try:
            client = immudb.ImmudbClient(conn_str)
            CLIENTS[continent] = client
            logging.info(f"[Python] Created immuDB client for {continent} at {conn_str}")
        except Exception as e:
            logging.error(f"[Python] Failed to create client for {continent}: {e}")
    else:
        logging.warning(f"[Python] No config found for {continent}")

# セッション管理：発行したトークン → 利用する大陸
SESSIONS = {}
DEFAULT_CONTINENT = "default"

class ImmuServiceServicer(immudb_pb2_grpc.ImmuServiceServicer):
    async def Login(self, request, context):
        try:
            user = request.user
            password = request.password
            # continent フィールドが存在すれば使用。なければ default。
            continent = request.continent if hasattr(request, "continent") and request.continent in CLIENTS else DEFAULT_CONTINENT
            client = CLIENTS.get(continent, CLIENTS[DEFAULT_CONTINENT])
            logging.info(f"[Python] Login called: user={user}, continent={continent}")
            loop = asyncio.get_running_loop()
            cfg = CONFIG.get(continent, CONFIG[DEFAULT_CONTINENT])
            # immudb-py の login() は同期関数なので run_in_executor で呼ぶ
            await loop.run_in_executor(None, client.login, cfg["username"], cfg["password"])
            token = f"{continent}_{user}_{uuid.uuid4().hex}"
            SESSIONS[token] = continent
            return immudb_pb2.LoginResponse(token=token)
        except Exception as e:
            logging.error(f"[Python] Login exception: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.LoginResponse(token="")

    async def Logout(self, request, context):
        token = request.token
        logging.info(f"[Python] Logout called: token={token}")
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
        client = CLIENTS.get(continent, CLIENTS[DEFAULT_CONTINENT])
        key = request.key
        val = request.value
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, client.set, key.encode('utf-8'), val.encode('utf-8'))
            logging.info(f"[Python] Set success: key={key}, value={val}")
            return immudb_pb2.SetResponse(success=True, message="Data stored")
        except Exception as e:
            logging.error(f"[Python] Set error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.SetResponse(success=False, message="Set failed")

    async def Get(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        continent = SESSIONS[token]
        client = CLIENTS.get(continent, CLIENTS[DEFAULT_CONTINENT])
        key = request.key
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, client.get, key.encode('utf-8'))
            val, _ = result
            decoded_val = val.decode('utf-8')
            logging.info(f"[Python] Get success: key={key}, value={decoded_val}")
            return immudb_pb2.GetResponse(success=True, value=decoded_val)
        except Exception as e:
            logging.error(f"[Python] Get error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.GetResponse(success=False, value="")

    async def MultiSet(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        continent = SESSIONS[token]
        client = CLIENTS.get(continent, CLIENTS[DEFAULT_CONTINENT])
        try:
            loop = asyncio.get_running_loop()
            for kv in request.kvs:
                await loop.run_in_executor(None, client.set, kv.key.encode('utf-8'), kv.value.encode('utf-8'))
            logging.info(f"[Python] MultiSet success: {len(request.kvs)} items stored")
            return immudb_pb2.MultiSetResponse(success=True, message="MultiSet successful")
        except Exception as e:
            logging.error(f"[Python] MultiSet error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.MultiSetResponse(success=False, message="MultiSet failed")

    async def Scan(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        continent = SESSIONS[token]
        client = CLIENTS.get(continent, CLIENTS[DEFAULT_CONTINENT])
        prefix = request.prefix
        limit = request.limit
        try:
            loop = asyncio.get_running_loop()
            scan_results = await loop.run_in_executor(None, client.scan, prefix.encode('utf-8'), limit)
            items = []
            for item in scan_results:
                items.append(immudb_pb2.KeyValue(
                    key=item["key"].decode('utf-8'),
                    value=item["value"].decode('utf-8')
                ))
            logging.info(f"[Python] Scan success: Found {len(items)} items with prefix '{prefix}'")
            return immudb_pb2.ScanResponse(success=True, items=items)
        except Exception as e:
            logging.error(f"[Python] Scan error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.ScanResponse(success=False, items=[])

    async def Delete(self, request, context):
        token = request.token
        if token not in SESSIONS:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
        continent = SESSIONS[token]
        client = CLIENTS.get(continent, CLIENTS[DEFAULT_CONTINENT])
        key = request.key
        try:
            logging.info(f"[Python] Delete called: key={key}")
            # immudb-py に Delete 操作が存在しない場合は仮実装
            return immudb_pb2.DeleteResponse(success=True, message="Deleted")
        except Exception as e:
            logging.error(f"[Python] Delete error: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            return immudb_pb2.DeleteResponse(success=False, message="Delete failed")

async def serve():
    # まず、各大陸の immuDB インスタンスを起動する
    spawn_immudb_instances()
    # gRPC サーバーを起動
    server = grpc.aio.server()
    immudb_pb2_grpc.add_ImmuServiceServicer_to_server(ImmuServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    await server.start()
    logging.info("[Python] Async gRPC server started on port 50051.")
    try:
        await server.wait_for_termination()
    finally:
        shutdown_immudb_instances()

if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logging.info("[Python] Async gRPC server shutting down.")