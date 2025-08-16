#!/usr/bin/env python3
"""
app.py

本番用エントリーポイント。
immudb.proto で定義された ImmuService (py_rs_immu_server.py) に対して
最低限の書き込み処理（Login -> Set -> Logout）を行うサンプル。

実行例:
    python app.py
事前にサーバー (py_rs_immu_server.py) が port=50051 で起動している必要があります。
"""

import asyncio
import grpc

# immudb.proto から生成した stubs
import immudb_pb2
import immudb_pb2_grpc

async def main():
    # 1) gRPC チャンネル作成
    channel = grpc.aio.insecure_channel("127.0.0.1:50051")
    stub = immudb_pb2_grpc.ImmuServiceStub(channel)

    # 2) Login
    login_req = immudb_pb2.LoginRequest(
        user="immudb",
        password="greg1024",
        continent="asia"  # 例としてアジアに接続
    )
    login_resp = await stub.Login(login_req)
    token = login_resp.token
    print(f"[app] Logged in => token={token}")

    # 3) Set (キー= "app_key", 値= "Hello from app.py")
    set_req = immudb_pb2.SetRequest(
        token=token,
        key="app_key",
        value=b"Hello from app.py"
    )
    set_resp = await stub.Set(set_req)
    print(f"[app] Set => success={set_resp.success}, msg={set_resp.message}")

    # 4) Logout
    logout_req = immudb_pb2.LogoutRequest(token=token)
    logout_resp = await stub.Logout(logout_req)
    print(f"[app] Logout => success={logout_resp.success}, msg={logout_resp.message}")

    # 5) チャンネルを閉じる
    await channel.close()
    print("[app] Done.")


if __name__ == "__main__":
    asyncio.run(main())
