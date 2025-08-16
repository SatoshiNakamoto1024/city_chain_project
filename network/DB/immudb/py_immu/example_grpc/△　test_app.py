#!/usr/bin/env python3
"""
test_app.py

複数の大陸(Asia, Europe, ... default)ごとに異なる immudb インスタンスを
WSL上で並行起動→ Flask を起動→ テスト→ 停止、を行うサンプルスクリプト。

前提:
- immudb_config.json で各大陸の host=127.0.0.1, port=XXXX を指定済み
- /home/satoshi/immudb_data/<continent> ディレクトリなどは事前に作成
- Linux版 immudb バイナリが `which immudb` で呼び出せる状態

app.py や immudb_handler.py などは最小限そのまま (上記5ファイル参照)。
"""

import subprocess
import time
import requests
import logging
import signal
import os
import json

# ログ設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Flask サーバーの URL（app.py は 127.0.0.1:5002 で起動）
BASE_URL = "http://127.0.0.1:5002"

# テスト用の定数 (キーとバリュー)
TEST_KEY = "transactions:test_key"
TEST_VALUE = {
    "message": "Hello, immuDB Federation!",
    "timestamp": "2025-02-16T12:00:00Z",
    "sender_continent": "Asia",  # 例
    "receiver_continent": "Europe"
}

# Flask アプリ（app.py）のパス
FLASK_APP_PATH = os.path.join(os.path.dirname(__file__), "app.py")
FLASK_CWD = os.path.dirname(FLASK_APP_PATH)

# 複数大陸の設定: immudb を起動するポートと dir
IMMUDB_INSTANCES = {
    "default": {
        "port": 3322,
        "dir": "/home/satoshi/immudb_data/tests/defaultdb"
    },
    "asia": {
        "port": 3323,
        "dir": "/home/satoshi/immudb_data/tests/asia"
    },
    "europe": {
        "port": 3324,
        "dir": "/home/satoshi/immudb_data/tests/europe"
    },
    "australia": {
        "port": 3325,
        "dir": "/home/satoshi/immudb_data/tests/australia"
    },
    "africa": {
        "port": 3326,
        "dir": "/home/satoshi/immudb_data/tests/africa"
    },
    "northamerica": {
        "port": 3327,
        "dir": "/mnt/d/city_chain_project/network/DB/immudb/data/tests/login/Default/northamerica"
    },
    "southamerica": {
        "port": 3328,
        "dir": "/home/satoshi/immudb_data/tests/southamerica"
    },
    "antarctica": {
        "port": 3329,
        "dir": "/home/satoshi/immudb_data/tests/antarctica"
    }
}


##############################################################################
#  immudb の起動・停止
##############################################################################

IMMUDB_PATH = "/usr/local/bin/immudb"

def start_all_immudb():
    """
    IMMUDB_INSTANCES で定義された各大陸の immudb を起動し、プロセス辞書を返す
    """
    processes = {}
    for continent, cfg in IMMUDB_INSTANCES.items():
        port = cfg["port"]
        data_dir = cfg["dir"]

        logging.info(f"🚀 immudb for {continent} を起動中... port={port}, dir={data_dir}")
        os.makedirs(data_dir, exist_ok=True)  # ディレクトリを作成(既にあってもOK)

        cmd = [
            IMMUDB_PATH,  # ← フルパスを使う
            "--port", str(port),
            "--address", "127.0.0.1",
            "--admin-password", "greg1024",
            "--dir", data_dir,
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # すぐに 1秒待ってログを取得してみる:
        time.sleep(1)
        if p.poll() is not None:  # プロセスが終了している
            out, _ = p.communicate()
            logging.error(f"immudb({continent}) crashed. Output:\n{out.decode()}")
    
        processes[continent] = p
    return processes

def wait_for_immudb_ready_all(timeout=15):
    """
    全 immudb インスタンスが起動するのを待つ（超簡易版: sleep）
    ちゃんとやるなら各portに対してソケット接続する。
    """
    logging.info("⌛ 全 immudb インスタンスの起動を待機しています (簡易sleep)")
    time.sleep(5)
    # 本当は each port に対して connect して成功確認すべき
    # ここでは省略
    logging.info("✅ 全 immudb 起動完了とみなします")

def stop_all_immudb(processes):
    """
    全 immudb インスタンスを停止する
    """
    logging.info("🛑 全 immudb インスタンスを停止中...")
    for continent, p in processes.items():
        logging.info(f"停止: immudb for {continent}")
        try:
            p.terminate()
        except Exception as e:
            logging.error(f"immudb({continent}) 停止失敗: {e}")
    # 全終了を待機
    for continent, p in processes.items():
        p.wait()


##############################################################################
#  Flask の起動・停止・待機 (単一)
##############################################################################

def wait_for_server_ready(timeout=15):
    """
    Flask サーバー起動チェック
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = requests.get(f"{BASE_URL}/", timeout=2)
            if r.status_code == 200:
                logging.info("✅ Flask サーバーが起動していることを確認しました。")
                return
        except Exception:
            pass
        time.sleep(1)
    logging.error("❌ Flask サーバーの起動がタイムアウトしました。")
    raise TimeoutError("Flask サーバー起動待機タイムアウト")

def start_flask():
    """ Flask サーバー (app.py) をバックグラウンドで起動 """
    logging.info("🚀 Flask サーバーを起動中...")
    p = subprocess.Popen(
        ["python3", FLASK_APP_PATH],
        cwd=FLASK_CWD,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    try:
        wait_for_server_ready()
    except Exception as e:
        logging.error("❌ Flask サーバーの起動に失敗しました。")
        p.kill()
        raise e
    logging.info("✅ Flask サーバーが起動しました。")
    return p

def stop_flask(process):
    """ Flask サーバープロセスを終了 """
    logging.info("🛑 Flask サーバーを停止中...")
    try:
        os.kill(process.pid, signal.SIGTERM)
    except Exception as e:
        logging.error(f"サーバープロセスの停止に失敗しました: {e}")
    process.wait()


##############################################################################
#  テスト項目 (例)
##############################################################################

def test_store_transaction():
    logging.info("=== Store Transaction Test ===")
    url = f"{BASE_URL}/store_transaction"
    data = {
        "key": TEST_KEY,
        # value は JSON 文字列化
        "value": json.dumps(TEST_VALUE),
        # 例: 送信元大陸を Asia
        "sender_continent": "Asia"
    }
    r = requests.post(url, json=data)
    if r.status_code == 200:
        logging.info(f"✅ store_transaction success: {r.json()}")
    else:
        logging.error(f"❌ store_transaction failed: {r.status_code} {r.text}")

def test_get_transaction():
    logging.info("=== Get Transaction Test ===")
    url = f"{BASE_URL}/get_transaction?key={TEST_KEY}&sender_continent=Asia"
    r = requests.get(url)
    if r.status_code == 200:
        result = r.json()
        logging.info(f"✅ get_transaction success: {result}")
    else:
        logging.error(f"❌ get_transaction failed: {r.status_code} {r.text}")

def test_multi_set():
    logging.info("=== MultiSet Test ===")
    url = f"{BASE_URL}/multi_set"
    data = {
        "transactions:tx1": {
            "amount": 100,
            "note": "Payment A",
            "timestamp": "2025-02-16T12:10:00Z",
            "sender_continent": "Europe",
            "receiver_continent": "Asia"
        },
        "transactions:tx2": {
            "amount": 200,
            "note": "Payment B",
            "timestamp": "2025-02-16T12:15:00Z",
            "sender_continent": "NorthAmerica",
            "receiver_continent": "SouthAmerica"
        },
    }
    r = requests.post(url, json=data)
    if r.status_code == 200:
        logging.info(f"✅ multi_set success: {r.json()}")
    else:
        logging.error(f"❌ multi_set failed: {r.status_code} {r.text}")

def test_scan_transactions():
    logging.info("=== Scan Transactions Test ===")
    url = f"{BASE_URL}/scan_transactions?prefix=transactions:&limit=10&sender_continent=Asia"
    r = requests.get(url)
    if r.status_code == 200:
        result = r.json()
        logging.info(f"✅ scan_transactions success: {result}")
    else:
        logging.error(f"❌ scan_transactions failed: {r.status_code} {r.text}")

##############################################################################
# メイン
##############################################################################

def main():
    logging.info("=== 複数大陸 immudb + Flask 統合テスト開始 ===")

    # 1. 全大陸ぶん immudb 起動
    immudb_processes = start_all_immudb()
    try:
        # 2. immudb 起動待機
        wait_for_immudb_ready_all()

        # 3. Flask 起動
        flask_process = start_flask()
        try:
            # 4. テスト実行
            test_store_transaction()
            time.sleep(2)
            test_get_transaction()
            test_multi_set()
            time.sleep(2)
            test_scan_transactions()
        finally:
            # Flask停止
            stop_flask(flask_process)
    finally:
        # 5. immudb停止
        stop_all_immudb(immudb_processes)

    logging.info("=== 複数大陸 immudb + Flask 統合テスト完了 ===")


if __name__ == "__main__":
    main()
