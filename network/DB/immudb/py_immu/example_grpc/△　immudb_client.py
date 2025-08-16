#!/usr/bin/env python3
"""
immudb_client.py

immuDB に対する gRPC クライアントを提供するモジュール。
"""

import grpc
import json
import logging
import base64
import immudb_pb2
import immudb_pb2_grpc

# ログ設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 設定ファイルのパス（環境に合わせてパスを変更してください）
CONFIG_PATH = "/mnt/d/city_chain_project/network/DB/config/config_json/immudb_config.json"

# 設定ファイルを読み込む
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    IMMUDATABASE_CONFIG = json.load(f)

class ImmuDBClient:
    def __init__(self, continent="default"):
        """
        指定された大陸のデータベースに接続する。
        設定ファイルから該当する接続情報を読み込む。
        """
        self.continent = continent
        # 設定ファイルに該当するキーがなければ default を使う
        self.config = IMMUDATABASE_CONFIG.get(continent, IMMUDATABASE_CONFIG["default"])
        self.channel = grpc.insecure_channel(f"{self.config['host']}:{self.config['port']}")
        self.stub = immudb_pb2_grpc.ImmuServiceStub(self.channel)
        self.token = None
        self.login()

    def login(self):
        """ immuDB にログインしてトークンを取得する """
        try:
            # LoginRequest はユーザー名とパスワードを文字列（または bytes）で渡す
            request = immudb_pb2.LoginRequest(
                user=self.config["username"],
                password=self.config["password"]
            )
            response = self.stub.Login(request)
            self.token = response.token
            logging.info(f"✅ Logged in to immuDB ({self.continent})")
        except grpc.RpcError as e:
            logging.error(f"❌ Login failed for {self.continent}: {e}")
            self.token = None

    def logout(self):
        """ immuDB からログアウトする """
        if not self.token:
            logging.warning("⚠️ No active session to logout.")
            return
        try:
            request = immudb_pb2.LogoutRequest(token=self.token)
            response = self.stub.Logout(request)
            if response.success:
                logging.info("✅ Logged out successfully")
                self.token = None
        except grpc.RpcError as e:
            logging.error(f"❌ Logout failed: {e}")

    def store_transaction(self, key, value_dict):
        """ JSON データを Base64 でエンコードして immuDB に保存する """
        if not self.token:
            logging.error("❌ No valid token. Please login first.")
            return False
        try:
            json_str = json.dumps(value_dict, ensure_ascii=False)
            encoded_value = base64.b64encode(json_str.encode()).decode()
            # SetRequest のフィールドに token, key, value を渡す
            request = immudb_pb2.SetRequest(
                token=self.token,
                key=key,
                value=encoded_value
            )
            response = self.stub.Set(request)
            if response.success:
                logging.info(f"✅ Transaction stored: {key}")
                return True
            else:
                logging.error(f"❌ Failed to store transaction: {key}")
                return False
        except grpc.RpcError as e:
            logging.error(f"❌ Store transaction error: {e}")
            return False

    def get_transaction(self, key):
        """ immuDB からデータを取得し、Base64 をデコードして JSON として返す """
        if not self.token:
            logging.error("❌ No valid token. Please login first.")
            return None
        try:
            request = immudb_pb2.GetRequest(
                token=self.token,
                key=key
            )
            response = self.stub.Get(request)
            if response.success:
                decoded_value = base64.b64decode(response.value).decode()
                return json.loads(decoded_value)
            else:
                logging.warning(f"⚠️ Key not found: {key}")
                return None
        except grpc.RpcError as e:
            logging.error(f"❌ Get transaction error: {e}")
            return None

    def multi_set(self, key_value_dict):
        """ 複数のキーと値を immuDB に保存する
            各値は JSON に変換後、Base64 エンコードされる
        """
        if not self.token:
            logging.error("❌ No valid token. Please login first.")
            return False
        try:
            key_value_list = [
                immudb_pb2.KeyValue(
                    key=key,
                    value=base64.b64encode(json.dumps(value_dict).encode()).decode()
                )
                for key, value_dict in key_value_dict.items()
            ]
            request = immudb_pb2.MultiSetRequest(
                token=self.token,
                kvs=key_value_list
            )
            response = self.stub.MultiSet(request)
            if response.success:
                logging.info(f"✅ MultiSet success: {len(key_value_dict)} transactions stored")
                return True
            else:
                logging.error("❌ MultiSet failed")
                return False
        except grpc.RpcError as e:
            logging.error(f"❌ MultiSet error: {e}")
            return False

    def scan_transactions(self, prefix, limit=10):
        """ 指定されたプレフィックスでスキャンして、見つかったトランザクションを返す """
        if not self.token:
            logging.error("❌ No valid token. Please login first.")
            return None
        try:
            request = immudb_pb2.ScanRequest(
                token=self.token,
                prefix=prefix,
                limit=limit
            )
            response = self.stub.Scan(request)
            if response.success:
                transactions = {
                    kv.key: json.loads(base64.b64decode(kv.value).decode())
                    for kv in response.items
                }
                logging.info(f"✅ Scan success: Found {len(transactions)} items with prefix '{prefix}'")
                return transactions
            else:
                logging.warning(f"⚠️ No transactions found with prefix: {prefix}")
                return None
        except grpc.RpcError as e:
            logging.error(f"❌ Scan error: {e}")
            return None