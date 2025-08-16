#!/usr/bin/env python3
"""
app.py

Flask API 経由で immuDB へのトランザクション保存・取得を行う DApps の実装版。
"""

import json
import os
from flask import Flask, request, jsonify
from immudb_handler import ImmuDBHandler

# 設定ファイルのパス
CONFIG_PATH = "/mnt/d/city_chain_project/network/DB/config/config_json/immudb_config.json"

# 設定ファイルを読み込む
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"❌ 設定ファイルが見つかりません: {CONFIG_PATH}")

# データベースハンドラーのキャッシュ
db_handlers = {}

def get_db_handler(continent):
    """
    設定に基づいてデータベースハンドラーを取得する。
    指定された大陸の設定が存在しない場合は、default の設定を使用する。
    """
    if continent not in CONFIG:
        continent = "default"

    if continent not in db_handlers:
        db_config = CONFIG[continent]
        db_handlers[continent] = ImmuDBHandler(db_config)  # 修正
    return db_handlers[continent]

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"status": "ok"}), 200

@app.route('/store_transaction', methods=['POST'])
def store_transaction():
    """
    POST リクエストで受け取った JSON データを immuDB に保存するエンドポイント。
    リクエストボディには "key" と "value" (value は JSON オブジェクト)、
    およびオプションで "sender_continent" を含めるものとする。
    """
    data = request.json
    key = data.get("key")
    value = data.get("value")
    sender_continent = data.get("sender_continent", "default")

    # value は JSON 文字列を受け取る想定
    if not key or not value:
        return jsonify({"status": "error", "message": "Invalid key or value format"}), 400

    # JSON文字列を再度 dict に戻す
    if isinstance(value, str):
        value_json = json.loads(value)
    else:
        value_json = value

    db_handler = get_db_handler(sender_continent)
    success = db_handler.store_transaction(key, value_json)
    if success:
        return jsonify({"status": "success", "message": f"Transaction {key} stored successfully."}), 200
    else:
        return jsonify({"status": "error", "message": f"Failed to store transaction {key}"}), 500

@app.route('/get_transaction', methods=['GET'])
def get_transaction():
    """
    GET リクエストで指定されたキーのトランザクションを取得するエンドポイント。
    クエリパラメータ "key" と、オプションで "sender_continent" を指定する。
    """
    key = request.args.get("key")
    sender_continent = request.args.get("sender_continent", "default")

    if not key:
        return jsonify({"status": "error", "message": "Missing key parameter"}), 400

    db_handler = get_db_handler(sender_continent)
    value = db_handler.get_transaction(key)
    
    if value is not None:
        return jsonify({"status": "success", "key": key, "value": value}), 200
    else:
        return jsonify({"status": "error", "message": "Key not found"}), 404

@app.route('/multi_set', methods=['POST'])
def multi_set():
    """
    複数のキーと値を immuDB に保存するエンドポイント。
    リクエストボディは JSON オブジェクトで、各プロパティ名がキー、
    その値が各トランザクションの内容（value は JSON オブジェクト＋ sender_continent などを含む）。
    """
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Invalid input format"}), 400

    success_list = []
    for key, value in data.items():
        sender_continent = value.get("sender_continent", "default")
        db_handler = get_db_handler(sender_continent)
        success = db_handler.store_transaction(key, value)
        if success:
            success_list.append(key)

    if success_list:
        return jsonify({"status": "success", "stored_keys": success_list}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to store any transactions"}), 500

@app.route('/scan_transactions', methods=['GET'])
def scan_transactions():
    """
    GET リクエストで指定されたプレフィックスのキーをスキャンするエンドポイント。
    クエリパラメータ "prefix"（デフォルトは "transactions:"）と "limit"（デフォルト 10）、
    およびオプションで "sender_continent" を指定する。
    """
    prefix = request.args.get("prefix", "transactions:")
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid limit parameter"}), 400
    sender_continent = request.args.get("sender_continent", "default")

    db_handler = get_db_handler(sender_continent)
    results = db_handler.scan_transactions(prefix, limit)
    
    if results:
        return jsonify({"status": "success", "transactions": results}), 200
    else:
        return jsonify({"status": "error", "message": "No transactions found"}), 404

if __name__ == "__main__":
    # Flask サーバーはホスト 0.0.0.0 のポート 5001 で起動　テスト用に
    app.run(host="0.0.0.0", port=5002, debug=True, use_reloader=False)
