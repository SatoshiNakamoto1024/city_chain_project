#!/usr/bin/env python3
"""
immudb_handler.py

immuDB とのインターフェースを提供するモジュール。
"""

import logging
import json
import base64
import immudb

# ログ設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 設定ファイルのパス
CONFIG_PATH = "/mnt/d/city_chain_project/network/DB/config/config_json/immudb_config.json"

# 設定ファイルを読み込む
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        IMMUDATABASE_CONFIG = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"❌ 設定ファイルが見つかりません: {CONFIG_PATH}")


class ImmuDBHandler:
    def __init__(self, config):
        self.host = config["host"]
        self.port = config["port"]
        self.user = config["username"]
        self.password = config["password"]
        self.database = config["database"]
        self.database_selected = False

        self.client = immudb.ImmudbClient(f"{self.host}:{self.port}")
        
        # まずログイン
        self.client.login(self.user, self.password)
        
        # さらに論理データベースを use する
        try:
            self.client.useDatabase(self.database)
            self.database_selected = True
            logging.info(f"✅ Connected to immuDB at {self.host}:{self.port} and using database '{self.database}'")
        except Exception as e:
            logging.error(f"❌ Database selection failed: {e}")

    def login(self):
        """ immuDB にログインしてデータベースを選択 """
        try:
            # ユーザー名とパスワードでログイン
            self.client.login(self.user, self.password)
            # JSON の "database" 項目に指定された論理データベース名を使用
            self.client.useDatabase(self.database)
            self.database_selected = True
            logging.info(f"✅ Connected to immuDB at {self.host}:{self.port} and using database '{self.database}'")
        except Exception as e:
            logging.error(f"❌ Database selection failed: {e}")

    def store_transaction(self, key, value_dict):
        """ JSON データを immuDB に保存 """
        if not self.database_selected:
            logging.error("❌ No database selected.")
            return False
        try:
            json_str = json.dumps(value_dict, ensure_ascii=False)
            logging.info(f"Encoded JSON string: {json_str}")
            encoded_value = base64.b64encode(json_str.encode()).decode()
            logging.info(f"Base64 encoded value: {encoded_value}")
            self.client.set(key.encode(), encoded_value.encode())
            logging.info(f"✅ Set success: {key}")
            return True
        except Exception as e:
            logging.error(f"❌ Set failed: {e}")
            return False

    def get_transaction(self, key):
        """ immuDB からデータを取得 """
        try:
            value, _ = self.client.get(key.encode())
            decoded_value = base64.b64decode(value).decode()
            logging.info(f"✅ Get success: key={key}, value={decoded_value}")
            return json.loads(decoded_value)
        except Exception as e:
            logging.error(f"❌ Get failed: {e}")
            return None

    def multi_set(self, key_value_dict):
        """ 複数のキーと値を immuDB に保存 """
        if not self.database_selected:
            logging.error("❌ No database selected.")
            return False
        try:
            for key, value_dict in key_value_dict.items():
                success = self.store_transaction(key, value_dict)
                if not success:
                    logging.error(f"❌ MultiSet failed for key: {key}")
                    return False
            logging.info(f"✅ MultiSet success: {len(key_value_dict)} items stored")
            return True
        except Exception as e:
            logging.error(f"❌ MultiSet error: {e}")
            return False

    def scan_transactions(self, prefix, limit=10):
        """ 指定されたプレフィックスでスキャンする処理
            - 保存したキーは、store_transaction で key.encode() された文字列
            - スキャン時も prefix.encode() して照合する
        """
        if not self.database_selected:
            logging.error("❌ No database selected.")
            return None
        try:
            scan_results = self.client.scan(prefix.encode(), limit=limit)
            # 返された各アイテムは、辞書形式で "key" と "value" がバイト列として格納されていると仮定
            parsed_results = {
                item["key"].decode(): json.loads(base64.b64decode(item["value"]).decode())
                for item in scan_results
            }
            logging.info(f"✅ Scan success: Found {len(parsed_results)} items with prefix '{prefix}'")
            return parsed_results
        except Exception as e:
            logging.error(f"❌ Scan failed: {e}")
            return None
        
    def get_db_handler(continent):
        if continent not in CONFIG:
            print(f"[DEBUG] continent={continent} not in CONFIG keys={list(CONFIG.keys())}")
            continent = "default"

        if continent not in db_handlers:
            db_config = CONFIG[continent]
            print(f"[DEBUG] Using config for {continent} = {db_config}")
            db_handlers[continent] = ImmuDBHandler(db_config)
        return db_handlers[continent]

