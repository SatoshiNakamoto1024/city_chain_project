#!/usr/bin/env python3
"""
py_immu_server.py (app_immudb.py)

このファイルは、immuDB への各種操作（ログイン、書き込み、読み出し、複数書き込み、スキャン、削除）を gRPC 経由で提供するサーバーです。
設定ファイル (JSON) から各大陸ごとの接続情報を読み込み、複数の immuDB クライアントを生成します。
"""

import os
import sys
import json
import grpc
import time
from concurrent import futures
import immudb  # pip install immudb-py

# カレントディレクトリをモジュール検索パスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 生成された gRPC スタブをインポート
import immudb_pb2
import immudb_pb2_grpc

# 設定ファイルのパス
CONFIG_PATH = "/mnt/d/city_chain_project/network/DB/config/config_json/immudb_config.json"

# 設定ファイルを読み込む
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        IMMUDATABASE_CONFIG = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"❌ 設定ファイルが見つかりません: {CONFIG_PATH}")


class ImmuServiceServicer(immudb_pb2_grpc.ImmuServiceServicer):
    def __init__(self):
        """
        各大陸（および default）の接続情報から immuDB クライアントを生成します。
        """
        self.clients = {}
        self.current_token = None
        self.continent = "default"
        
        # 各大陸の接続情報ごとに immudb.ImmudbClient を生成
        for continent, config in IMMUDATABASE_CONFIG.items():
            connection_str = f"{config['host']}:{config['port']}"
            self.clients[continent] = immudb.ImmudbClient(connection_str)
            print(f"[Python] Client created for {continent} at {connection_str}")

    def get_client(self, continent):
        """ 指定された大陸の immuDB クライアントを返します。 """
        return self.clients.get(continent, self.clients["default"])

    def Login(self, request, context):
        try:
            user = request.user
            password = request.password
            # リクエストに continent が含まれていればそれを使用、なければ default を使用
            continent = request.continent if hasattr(request, "continent") and request.continent in self.clients else "default"
            client = self.get_client(continent)
            print(f"[Python] Login called: user={user}, continent={continent}")
            # 各大陸の設定情報から、ユーザー名・パスワードでログインを実施
            config = IMMUDATABASE_CONFIG.get(continent, IMMUDATABASE_CONFIG["default"])
            client.login(config["username"], config["password"])
            # （本来はトークン管理を行うべきですが、ここではダミートークンを生成）
            self.current_token = f"token_{user}_{continent}"
            self.continent = continent
            return immudb_pb2.LoginResponse(token=self.current_token)
        except Exception as e:
            print(f"[Python] Login exception: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return immudb_pb2.LoginResponse(token="")

    def Logout(self, request, context):
        token = request.token
        print(f"[Python] Logout called: token={token}")
        if token == self.current_token:
            self.current_token = None
            return immudb_pb2.LogoutResponse(success=True, message="Logout OK")
        else:
            return immudb_pb2.LogoutResponse(success=False, message="Invalid token")

    def Set(self, request, context):
        key = request.key
        val = request.value
        client = self.get_client(self.continent)
        try:
            client.set(key.encode('utf-8'), val.encode('utf-8'))
            print(f"[Python] Set called: key={key}, value={val} - SUCCESS")
            return immudb_pb2.SetResponse(success=True, message="Data stored in immuDB")
        except Exception as e:
            print(f"[Python] Set error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return immudb_pb2.SetResponse(success=False, message="Set failed")

    def Get(self, request, context):
        key = request.key
        client = self.get_client(self.continent)
        try:
            val, _ = client.get(key.encode('utf-8'))
            decoded_val = val.decode('utf-8')
            print(f"[Python] Get called: key={key}, value={decoded_val} - SUCCESS")
            return immudb_pb2.GetResponse(success=True, value=decoded_val)
        except Exception as e:
            print(f"[Python] Get error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return immudb_pb2.GetResponse(success=False, value="")

    def MultiSet(self, request, context):
        try:
            KVs = request.kvs  # KVs は KeyValue のリスト
            client = self.get_client(self.continent)
            for kv in KVs:
                key = kv.key
                value = kv.value
                client.set(key.encode('utf-8'), value.encode('utf-8'))
            print(f"[Python] MultiSet SUCCESS: {len(KVs)} items stored")
            return immudb_pb2.MultiSetResponse(success=True, message="MultiSet successful")
        except Exception as e:
            print(f"[Python] MultiSet ERROR: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return immudb_pb2.MultiSetResponse(success=False, message="MultiSet failed")

    def Scan(self, request, context):
        try:
            prefix = request.prefix.encode('utf-8')
            limit = request.limit
            client = self.get_client(self.continent)
            scan_results = client.scan(prefix=prefix, limit=limit)
            items = [
                immudb_pb2.KeyValue(key=item['key'].decode('utf-8'), value=item['value'].decode('utf-8'))
                for item in scan_results
            ]
            print(f"[Python] Scan SUCCESS: Found {len(items)} items with prefix '{request.prefix}'")
            return immudb_pb2.ScanResponse(success=True, items=items)
        except Exception as e:
            print(f"[Python] Scan ERROR: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return immudb_pb2.ScanResponse(success=False, items=[])

    def Delete(self, request, context):
        token = request.token
        key = request.key
        client = self.get_client(self.continent)
        print(f"[Python] Delete called, token={token}, key={key}")
        return immudb_pb2.DeleteResponse(success=True, message="Deleted")


def serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        immudb_pb2_grpc.add_ImmuServiceServicer_to_server(ImmuServiceServicer(), server)
        # gRPC サーバーはポート 50051 で起動します
        server.add_insecure_port('[::]:50051')
        server.start()
        print("[Python] gRPC server started on port 50051.")
        server.wait_for_termination()
    except Exception as e:
        print(f"[Python] Server encountered an error: {e}")


if __name__ == '__main__':
    serve()
