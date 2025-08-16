# py_immu_server.py
import os
import sys
import time
from concurrent import futures

import grpc
import immudb  # pip install immudb-py

# カレントディレクトリをモジュール検索パスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 生成されたスタブファイルはカレントディレクトリにある前提
import immudb_pb2
import immudb_pb2_grpc
# schema_pb2 は immudb_pb2 で参照されるので、個別の import は不要（必要なら import してください）

class ImmuServiceServicer(immudb_pb2_grpc.ImmuServiceServicer):
    def __init__(self):
        # Python 側で immudb-py を使い、実際の immuDB に接続（例: localhost:3322）
        self.client = immudb.ImmudbClient("127.0.0.1:3322")
        self.current_token = None

    def Login(self, request, context):
        try:
            user = request.user
            password = request.password
            print(f"[Python] Login called: user={user}")
            # 実際の処理（例: immuDBへのログイン）をここで実施
            self.current_token = "dummy_token_" + user
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
        try:
            # immuDB にデータを保存
            self.client.set(key.encode('utf-8'), val.encode('utf-8'))
            print(f"[Python] Set called: key={key}, value={val} - SUCCESS")
            return immudb_pb2.SetResponse(success=True, message="Data stored in immuDB")
        except Exception as e:
            # 例外発生時は gRPC のエラーメッセージを返す
            print(f"[Python] Set error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return immudb_pb2.SetResponse(success=False, message="Set failed")

    def Get(self, request, context):
        key = request.key
        try:
            # immuDB からデータを取得
            val, _ = self.client.get(key.encode('utf-8'))
            decoded_val = val.decode('utf-8')
            print(f"[Python] Get called: key={key}, value={decoded_val} - SUCCESS")
            return immudb_pb2.GetResponse(success=True, value=decoded_val)
        except Exception as e:
            # 例外発生時のエラーハンドリング
            print(f"[Python] Get error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return immudb_pb2.GetResponse(success=False, value="")

    def MultiSet(self, request, context):
        try:
            token = request.token
            KVs = request.kvs  # KVs は KeyValue のリスト
            for kv in KVs:
                key = kv.key
                value = kv.value
                self.client.set(key.encode('utf-8'), value.encode('utf-8'))

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

            scan_results = self.client.scan(prefix=prefix, limit=limit)

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
        print(f"[Python] Delete called, token={token}, key={key}")
        return immudb_pb2.DeleteResponse(success=True, message="Deleted")

def serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        immudb_pb2_grpc.add_ImmuServiceServicer_to_server(ImmuServiceServicer(), server)
        server.add_insecure_port('[::]:50051')
        server.start()
        print("[Python] gRPC server started on port 50051.")
        server.wait_for_termination()
    except Exception as e:
        print(f"[Python] Server encountered an error: {e}")

if __name__ == '__main__':
    serve()
