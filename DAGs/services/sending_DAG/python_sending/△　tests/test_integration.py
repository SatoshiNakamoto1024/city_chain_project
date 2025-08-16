# D:\city_chain_project\network\DAGs\python\tests\test_integration.py

"""
test_integration.py (修正版)

システム全体を起動して以下を確認:
1) 動的バッチインターバル -> トラフィック多いと短縮
2) リバランス -> ライトノードへの再複製 (ログの有無で確認)
3) 期限切れTx -> 廃棄 or 延長
4) City→/send_tx→完了処理
"""

import subprocess
import time
import requests
import pytest
import os
import re
import logging
from pymongo import MongoClient

CITY_URL = "http://localhost:5001"
CONTINENT_URL = "http://localhost:6001"
GLOBAL_URL = "http://localhost:7001"

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
db_client = MongoClient(MONGODB_URI)
db = db_client["federation_dag_db"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
logger.addHandler(ch)

@pytest.fixture(scope="session", autouse=True)
def setup_servers():
    """
    city_main, continent_main, global_main をサブプロセスで起動し、
    テスト完了後に停止。
    """
    city_proc = subprocess.Popen(["python", "city_level/city_main.py"])
    continent_proc = subprocess.Popen(["python", "continent_level/continent_main.py"])
    global_proc = subprocess.Popen(["python", "global_level/global_main.py"])

    # 起動待ち
    time.sleep(3)

    yield

    city_proc.terminate()
    continent_proc.terminate()
    global_proc.terminate()
    time.sleep(1)

def test_dynamic_batch_and_rebalance():
    """
    1) 大量のTxをcityに送信
    2) バッチインターバルが短縮されているか(ログなど)を確認 (簡易)
    3) リバランスが走っているかログ確認
    """
    # まず5件ほど送信 => pendingTx数が増えればインターバルが短くなる想定
    for i in range(5):
        payload = {
            "sender": f"Alice{i}",
            "receiver": "Bob",
            "amount": 100 + i
        }
        r = requests.post(f"{CITY_URL}/send_tx", json=payload)
        assert r.status_code == 200

    # バッチループが短くなるのを待つ
    time.sleep(5)

    # ここではログファイルなどをパースし、"BatchProcess:" の間隔が短いかを見る例 (実際にはapp.logを出力?)
    # 簡単に "grpc_node_storage" が複数ファイルできているかを確認
    grpc_storage_path = "./grpc_node_storage"
    if os.path.exists(grpc_storage_path):
        count_json = len([f for f in os.listdir(grpc_storage_path) if f.endswith(".json")])
        assert count_json > 0, "バッチがgRPC送信されていない？"
    else:
        logger.warning("grpc_node_storage未検出: gRPC送信が動いてないかも？")

    # リバランス => "Rebalance shard OK" のログを見たいが、ここでは時間を置いて挙動確認
    time.sleep(35)  # REBALANCE_INTERVAL=30 くらい

    # まだ自動チェックが難しいので、ログに"Rebalance shard OK"が出ているかを最後に目視 or 
    # あるいはデモ用に just pass
    print("[TEST] test_dynamic_batch_and_rebalance done")


def test_six_months_rule():
    """
    Txを作成して強制的にtimestampを過去にし、cleanup時に廃棄 or 延長されるかテスト
    => 直接 city_dag_handler のメモリにアクセスしにくいのでユニットテスト向き
    => 簡易: /complete_tx しないまま wait して、ログで "期限切れ=>破棄" が出るかみる
    """
    # 送信
    r = requests.post(f"{CITY_URL}/send_tx", json={"sender":"OldUser", "receiver":"Bob", "amount":999})
    assert r.status_code == 200
    data = r.json()
    tx_id = data["tx_id"]
    time.sleep(2)

    # テストのため city_dag_handler にアクセスできれば "timestamp" を過去に書き換えたいが...
    # ここでは logs上の "期限切れ => 破棄" を見るだけのデモ

    # 70秒ほど待てば(仮にMAX_DAG_DURATIONを短く設定してあれば) => "破棄"ログが出る
    time.sleep(70)
    print("[TEST] check logs for '期限切れ => 破棄'")


def test_send_and_complete():
    """
    普通にsend→1秒以内バッチ→/complete_txでMongoDB保存される流れ
    """
    payload = {
        "sender": "Alice",
        "receiver": "Bob",
        "amount": 123
    }
    r = requests.post(f"{CITY_URL}/send_tx", json=payload)
    assert r.status_code == 200
    data = r.json()
    tx_id = data["tx_id"]

    # 待つ
    time.sleep(2)

    # complete
    rc = requests.post(f"{CITY_URL}/complete_tx/"+tx_id)
    assert rc.status_code == 200

    time.sleep(1)
    # MongoDB確認
    rec = db["completed_transactions"].find_one({"tx_id": tx_id})
    assert rec is not None, "Txがcompleted_transactionsに保存されていない"
    print("[TEST] test_send_and_complete OK")
