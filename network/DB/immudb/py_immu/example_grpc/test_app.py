#!/usr/bin/env python3
"""
test_app.py

- サーバー(py_rs_immu_server.py)が 0.0.0.0:50051 で稼働していると仮定
- immudb.proto と同じ stubs (immudb_pb2, immudb_pb2_grpc) を利用し、
  Rust と同じ A->B, C->D トランザクションテストを行う。

Usage:
    python test_app.py
"""

import asyncio
import grpc

import immudb_pb2
import immudb_pb2_grpc

async def single_test(stub: immudb_pb2_grpc.ImmuServiceStub, token: str):
    """
    単発で Set/Get/MultiSet/Scan を行う簡易テスト。
    """
    print("[single_test] Start")

    # 1) Set
    set_resp = await stub.Set(immudb_pb2.SetRequest(
        token=token,
        key="test_key",
        value=b"Hello from Python single_test"
    ))
    print(f"[single_test] Set => success={set_resp.success}, msg={set_resp.message}")

    # 2) Get
    get_resp = await stub.Get(immudb_pb2.GetRequest(
        token=token,
        key="test_key"
    ))
    if get_resp.success:
        print(f"[single_test] Get => {get_resp.value}")
    else:
        print("[single_test] Get fail")

    # 3) MultiSet
    multi_resp = await stub.MultiSet(immudb_pb2.MultiSetRequest(
        token=token,
        kvs=[
            immudb_pb2.KeyValue(key=b"multi_key1", value=b"Value1"),
            immudb_pb2.KeyValue(key=b"multi_key2", value=b"Value2"),
        ]
    ))
    print(f"[single_test] MultiSet => success={multi_resp.success}, msg={multi_resp.message}")

    # 4) Scan
    scan_resp = await stub.Scan(immudb_pb2.ScanRequest(
        token=token,
        prefix="test",
        desc=False,
        limit=10
    ))
    if scan_resp.success:
        print(f"[single_test] Scan => found {len(scan_resp.items)} items")
        for kv in scan_resp.items:
            print(f"   Key={kv.key}, Value={kv.value}")
    else:
        print("[single_test] Scan fail")

    print("[single_test] Done")


async def four_continent_transactions(stub: immudb_pb2_grpc.ImmuServiceStub):
    """
    同時に A->B, C->D を行う。4大陸それぞれにログインし、
    Asia/EU, North/South へ書き込み & 取得。
    """
    # 1) Login to Asia
    asia_login = await stub.Login(immudb_pb2.LoginRequest(
        user="immudb", password="greg1024", continent="asia"
    ))
    token_asia = asia_login.token

    # 2) Login to Europe
    europe_login = await stub.Login(immudb_pb2.LoginRequest(
        user="immudb", password="greg1024", continent="europe"
    ))
    token_eu = europe_login.token

    # 3) Login to North
    north_login = await stub.Login(immudb_pb2.LoginRequest(
        user="immudb", password="greg1024", continent="northamerica"
    ))
    token_na = north_login.token

    # 4) Login to South
    south_login = await stub.Login(immudb_pb2.LoginRequest(
        user="immudb", password="greg1024", continent="southamerica"
    ))
    token_sa = south_login.token

    # ほぼ同時に書き込み: A->B, C->D
    async def do_a_to_b():
        # A(asia) 送金
        await stub.Set(immudb_pb2.SetRequest(
            token=token_asia,
            key="Tx_A->B",
            value=b"A(asia) -> B(europe): 100harmony tokens"
        ))
        # B(europe) 受信
        await stub.Set(immudb_pb2.SetRequest(
            token=token_eu,
            key="Tx_A->B",
            value=b"B(europe) received 100harmony tokens from A(asia)"
        ))
    async def do_c_to_d():
        # C(north) 送金
        await stub.Set(immudb_pb2.SetRequest(
            token=token_na,
            key="Tx_C->D",
            value=b"C(north) -> D(south): 300harmony tokens"
        ))
        # D(south) 受信
        await stub.Set(immudb_pb2.SetRequest(
            token=token_sa,
            key="Tx_C->D",
            value=b"D(south) received 300harmony tokens from C(north)"
        ))

    await asyncio.gather(do_a_to_b(), do_c_to_d())

    # 取得して確認
    # Asia
    a_get = await stub.Get(immudb_pb2.GetRequest(token=token_asia, key="Tx_A->B"))
    # Europe
    b_get = await stub.Get(immudb_pb2.GetRequest(token=token_eu, key="Tx_A->B"))
    # North
    c_get = await stub.Get(immudb_pb2.GetRequest(token=token_na, key="Tx_C->D"))
    # South
    d_get = await stub.Get(immudb_pb2.GetRequest(token=token_sa, key="Tx_C->D"))

    print("[4-Continent Test] Asia DB =>", a_get.value)
    print("[4-Continent Test] EuropeDB =>", b_get.value)
    print("[4-Continent Test] NorthDB =>", c_get.value)
    print("[4-Continent Test] SouthDB =>", d_get.value)

    # Logout
    await stub.Logout(immudb_pb2.LogoutRequest(token=token_asia))
    await stub.Logout(immudb_pb2.LogoutRequest(token=token_eu))
    await stub.Logout(immudb_pb2.LogoutRequest(token=token_na))
    await stub.Logout(immudb_pb2.LogoutRequest(token=token_sa))

    print("[4-Continent Test] Done (A->B, C->D)")


async def run_test():
    # 1) チャンネルを作成 (aio)
    channel = grpc.aio.insecure_channel("127.0.0.1:50051")
    stub = immudb_pb2_grpc.ImmuServiceStub(channel)

    # 2) Asia に Login
    login_resp = await stub.Login(immudb_pb2.LoginRequest(
        user="immudb",
        password="greg1024",
        continent="asia"
    ))
    token = login_resp.token
    print(f"[TEST] Logged in (asia) => token={token}")

    # 3) 単発テスト
    await single_test(stub, token)

    # 4) Logout
    await stub.Logout(immudb_pb2.LogoutRequest(token=token))
    print("[TEST] Logged out (asia).")

    # 5) 4大陸同時トランザクションテスト
    await four_continent_transactions(stub)

    # 6) close channel
    await channel.close()


def main():
    asyncio.run(run_test())


if __name__ == "__main__":
    main()
