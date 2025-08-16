"""
This module is the main application file for the Flask app.

It includes route definitions, service calls, and application configurations.
"""
from ast import Attribute
from dotenv import load_dotenv
import sys
import os
import random
import threading
import time
import openai
import requests
import json
import base64  # これを追加
import uuid  # ここでuuidをインポート
import hashlib
import pytz
from flask import Flask, request, jsonify, redirect, url_for
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from flask_cors import CORS  # ここでCORSをインポート
from datetime import timedelta  # timedeltaをインポート
from datetime import timezone
from datetime import datetime
from pymongo import MongoClient
sys.path.append(r"D:\city_chain_project\ntru\dilithium-py\src")
from dilithium_py.dilithium.dilithium import Dilithium
sys.path.append(r"D:\city_chain_project\ntru\NTRU-Encryption\Files")
from ntru_encryption import Ntru  # これも適切なパスが必要です
from fractions import Fraction  # 修正済み
from poly import extEuclidPoly
from typing import List, Tuple, Any, Dict
from random import choice
from math import gcd
from dataclasses import dataclass
# immuDB 関連
import grpc
import base64
from immudb_proto import immu_service_client
from immudb_proto.immu_service_client import ImmuServiceClient
from immudb_proto import schema_pb2 as schema
# immuDB でウォレットを分けて記録する際の Prefix
IMMUDB_WALLET_PREFIX = "wallet_"

# walletをDBに定義
mongo_client = MongoClient("mongodb://localhost:27017")
wallet_collection = mongo_client['wallet_db']['wallets']


@dataclass
class JournalEntry:
    date: datetime
    sender: str
    description: str
    debit_account: str
    credit_account: str
    amount: float
    judgment_criteria: dict
    transaction_id: str


# 科目リスト
accounts = {
    "assets": ["愛貨", "未使用愛貨", ...],
    "liabilities": ["未実施行動の債務", ...],
    "equity": ["繰越愛貨", ...],
    "revenue": ["愛の行動受取", ...],
    "expenses": ["愛の行動消費", ...],
    "netprofit": ["愛貨消費による貢献度", ...]
}

# 科目タイプのマッピングを定義
account_type_mapping = {
    # 資産科目（assets）
    "愛貨": "assets",
    "未使用愛貨": "assets",
    "他者からの未収愛貨": "assets",
    # 追加の資産科目...

    # 負債科目（liabilities）
    "未実施行動の債務": "liabilities",
    "目標未達成による債務": "liabilities",
    # 追加の負債科目...

    # 純資産科目（equity）
    "繰越愛貨": "equity",
    "愛貨評価差額": "equity",
    # 追加の純資産科目...

    # 収益科目（revenue）
    "愛の行動受取": "revenue",
    "目標達成による愛貨の獲得": "revenue",
    # 追加の収益科目...

    # 費用科目（expenses）
    "愛の行動消費": "expenses",
    "愛貨感謝返礼費用": "expenses",
    # 追加の費用科目...
}

criteria_template = {
    "purpose": "",
    "expected_outcome": "",
    "action_specificity": "",
    "duration": "",
    "reciprocity": ""
}

# 現在のディレクトリ（dappsディレクトリ）をパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# グローバル変数で送信履歴を保持
recent_transactions = []
# グローバル変数としてNTRUインスタンスを管理
ntru_instance = None

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
# セキュリティ上、長くて推測しにくいキーを設定してください
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
jwt = JWTManager(app)


# immuDBにおけるウォレット操作用ヘルパーを追加
def connect_to_immudb():
    """
    immuDBに接続するためのヘルパー関数。
    実際には設定ファイルや環境変数からhost, portなどを読み込むのが望ましい。
    """
    # 例: localhost:3322 で immuDB が起動していると仮定
    channel = grpc.insecure_channel("localhost:3322")
    client = ImmuServiceClient(channel)
    # ログイン (ユーザー名・パスワードは本番環境では安全に管理する必要あり)
    login_req = schema.LoginRequest(user="immudb", password="immudb")
    client.service.Login(login_req)
    return client


def save_wallet_to_immudb(user_id: str, balance: float):
    """
    user_idに紐づくウォレット残高をimmuDBに保存する(上書き)。
    """
    client = connect_to_immudb()
    wallet_key = (IMMUDB_WALLET_PREFIX + user_id).encode("utf-8")
    wallet_value = str(balance).encode("utf-8")

    set_request = schema.SetRequest(
        kvs=[schema.KeyValue(key=wallet_key, value=wallet_value)]
    )
    client.service.Set(set_request)
    print(f"[immuDB] Wallet for user {user_id} saved with balance={balance}")


def get_wallet_from_immudb(user_id: str) -> float:
    """
    immuDBからウォレット残高を取得する。
    """
    client = connect_to_immudb()
    wallet_key = (IMMUDB_WALLET_PREFIX + user_id).encode("utf-8")
    get_req = schema.GetRequest(key=wallet_key)
    try:
        get_res = client.service.Get(get_req)
        wallet_bytes = get_res.value
        balance_str = wallet_bytes.decode("utf-8")
        return float(balance_str)
    except Exception:
        # まだkeyが存在しない場合は残高0として扱う
        return 0.0


def update_wallet_in_immudb(user_id: str, amount: float):
    """
    immuDB上のウォレット残高をamountだけ加算(減算)する。
    """
    current_balance = get_wallet_from_immudb(user_id)
    new_balance = current_balance + amount
    if new_balance < 0:
        new_balance = 0  # 負にしないなどの対策は必要に応じて
    save_wallet_to_immudb(user_id, new_balance)
    return new_balance


def initialize_ntru():
    global ntru_instance
    # 例: N=11, p=3, q=128 などパラメータを設定 (本番パラメータとは異なる小さい例)
    ntru_instance = Ntru(N_new=11, p_new=3, q_new=128)

    # 以下、秘密鍵 f, g, d などを与えて公開鍵を作る:
    f_new = [1, -1, 0, 1]  # 例: 適当な ternary poly
    g_new = [0, 1, -1, 1]
    d_new = 7

    # 公開鍵生成
    ntru_instance.genPublicKey(f_new, g_new, d_new)
    print("NTRU public key:", ntru_instance.getPublicKey())

# Flask起動前に NTRU初期化
initialize_ntru()


def generate_ntru_keys():
    # 公開鍵と秘密鍵を生成する処理をここに記述
    public_key = "dummy_public_key"  # 仮のデータ
    private_key = "dummy_private_key"  # 仮のデータ
    return public_key, private_key


def is_invertible(poly, q):
    """多項式がモジュラス q の下で可逆かどうか確認"""
    try:
        # 簡易的なチェック：和が q と互いに素か確認
        return gcd(sum(poly), q) == 1
    except ZeroDivisionError:
        return False


def is_valid_ntru_poly(poly: List[int]) -> bool:
    """
    NTRU用の条件を満たしているかを確認する。
    例: 係数が-1, 0, 1に限定され、正負の係数が一定範囲内にあることを確認。
    """
    count_pos = sum(1 for x in poly if x == 1)
    count_neg = sum(1 for x in poly if x == -1)
    count_zero = len(poly) - count_pos - count_neg

    # ここで条件を緩和
    if count_pos < 0 or count_neg < 0:
        return False
    # ...さらに厳しい制限があれば
    # 例：gcd(sum(poly), q) == 1 とか
    return True


def generate_polynomial(N: int, values: Tuple[int, ...]) -> List[Fraction]:
    max_attempts = 1000
    attempts = 0

    while attempts < max_attempts:
        poly = [random.choice(values) for _ in range(N)]
        if is_valid_ntru_poly(poly):
            return [Fraction(x) for x in poly]
        print(f"Attempt {attempts + 1}: Invalid polynomial: {poly}")  # 追加したログ
        attempts += 1

    raise RuntimeError(
        f"Failed to generate a valid polynomial after {max_attempts} attempts."
    )


# 鍵ペア生成の実行
ntru_public_key, ntru_private_key = generate_ntru_keys()

if ntru_public_key and ntru_private_key:
    print("NTRU Key Pair Generated Successfully!")
    print("Ntru Public Key:", ntru_public_key)
    print("Ntru Private Key:", ntru_private_key)
else:
    print("Failed to generate NTRU Key Pair.")


# 公開鍵と秘密鍵を保存
def save_keys(public_key, private_key):
    with open("keys.json", "w") as f:
        json.dump({"public_key": public_key, "private_key": private_key}, f)


save_keys(ntru.getPublicKey(), ntru.f)  # ntru.f は秘密鍵


def sign_with_dilithium(data, private_key):
    try:
        signature = dilithium_instance.generate_signature(private_key, data)
        return signature
    except Exception as e:
        raise ValueError(f"Dilithium signing failed: {e}")


def verify_dilithium_signature(data, signature, public_key):
    try:
        return dilithium_instance.verify_signature(public_key, data, signature)
    except Exception as e:
        raise ValueError(f"Dilithium signature verification failed: {e}")


# Dilithiumインスタンスの作成と初期化
parameter_set = {
    "d": 14,
    "k": 4,
    "l": 4,
    "eta": 2,
    "tau": 39,
    "omega": 80,
    "gamma_1": 131072,
    "gamma_2": 95232,
    "beta": 196,
}

dilithium_instance = Dilithium(parameter_set)

# 公開鍵と秘密鍵の初期化
pq_public_key, pq_private_key = dilithium_instance.keygen()


# passwords.jsonを読み込む関数
def load_passwords_data():
    file_path = os.path.join(os.path.dirname(__file__), "passwords.json")

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"{file_path} not found. Please check the file path."
        )

    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


# indivisuals.jsonを読み込む関数
def load_individuals_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'indivisuals.json')

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"{file_path} not found. Please check the file path."
        )

    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


# passwords.json と individuals.json のデータを読み込む
passwords_data = load_passwords_data()
individuals_data = load_individuals_data()


def hash_password(password):
    """パスワードをSHA-256でハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()


# ログイン用エンドポイント
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # passwords.json から該当ユーザーのパスワードハッシュを取得
    user_password_data = next(
        (user for user in passwords_data if user["username"] == username), None
    )
    if not user_password_data:
        return jsonify(message='ユーザー名が存在しません'), 401

    # パスワードをハッシュ化して照合
    hashed_password = hash_password(password)
    if hashed_password != user_password_data.get("password_hash"):
        return jsonify(message='パスワードが正しくありません'), 401

    # individuals.json から該当ユーザーの個人情報を取得
    user_individual_data = next(
        (user for user in individuals_data if user["name"] == username), None
    )
    if not user_individual_data:
        return jsonify(message='個人情報が見つかりません'), 401

    # トークン生成
    try:
        access_token = create_access_token(
            identity=username, expires_delta=timedelta(hours=1)
        )
        return jsonify(token=access_token), 200
    except Exception as e:
        return jsonify(message='トークン生成エラー: ' + str(e)), 500


def get_continent_from_municipality(municipality_name):
    global municipalities_data  # グローバル変数を使用
    for continent, data in municipalities_data.items():
        if 'cities' in data:
            for city in data['cities']:
                if city['name'] == municipality_name:
                    return continent
    return 'Default'  # 該当なしの場合は 'Default' を返す


# Flaskポートを取得する関数
def get_flask_port(continent_name):
    # 大陸名のflask_portを取得
    if continent_name in municipalities_data:
        flask_port = municipalities_data[continent_name].get("flask_port")
        if flask_port:
            return int(flask_port)

    # Defaultのflask_portを取得
    return int(municipalities_data["Default"]["flask_port"])


# MongoDB設定ファイルパス
MONGODB_CONFIG_PATH = (
    r"D:\city_chain_project\config\config_json\mongodb_config.json"
)


# MongoDB設定ファイルを読み込む
def load_mongodb_config():
    try:
        with open(MONGODB_CONFIG_PATH, 'r', encoding='utf-8') as file:
            content = file.read()
            print("MongoDB config content:", content)  # ファイルの内容を表示してデバッグ
            return json.loads(content)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Error: '{MONGODB_CONFIG_PATH}' not found. Please check the path."
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Error decoding JSON from '{MONGODB_CONFIG_PATH}': {e}"
        )


# グローバル変数に設定を読み込む
mongodb_config = load_mongodb_config()

# ファイルパスを指定
mongodb_config_path = "mongodb_config.json"

# 確認用
print("Final MongoDB Config:", mongodb_config)


# URIの最後のスラッシュ / の後の部分を取得すればデータベース名が得られる
def get_database_name(mongo_uri):
    return mongo_uri.rsplit('/', 1)[-1]


# MongoDB URI を取得する関数
def get_mongo_uri(instance_type, continent):
    try:
        if instance_type in mongodb_config and continent in mongodb_config[
            instance_type
        ]:
            return mongodb_config[instance_type][continent]
        elif instance_type in mongodb_config and 'default' in mongodb_config[
            instance_type
        ]:
            return mongodb_config[instance_type]['default']
        else:
            raise ValueError(
                f"MongoDB URI not found for instance type '{instance_type}'"
                f"continent '{continent}'"
            )
    except Exception as e:
        raise RuntimeError(f"Error retrieving MongoDB URI: {e}")


# MongoDB コネクションを取得する
def get_mongo_connection(instance_type, continent):
    mongo_uri = get_mongo_uri(instance_type, continent)
    client = MongoClient(mongo_uri)
    db_name = get_database_name(mongo_uri)
    db = client[db_name]
    return db


# 上記の接続関数を用いて、特定のコレクションにアクセスする例
def add_journal_entry(entry, continent="Default"):
    db = get_mongo_connection("journal_entries", continent)
    collection = db["journal_entries"]
    collection.insert_one(entry)


# サンプルエントリ
entry_data = {
    "date": "2024-11-10",
    "description": "Sample journal entry",
    "debit_account": "愛貨",
    "credit_account": "愛貨受取",
    "amount": 100,
    "transaction_id": "sample_txn_001"
}

# アジアのjournal_entriesコレクションにエントリを追加
add_journal_entry(entry_data, "Asia")

# Example usage: send_pending のアジア用インスタンスを取得
try:
    mongo_client = get_mongo_connection("send_pending", "Asia")
    send_pending_collection = mongo_client['transactions_db'][
        'send_pending_transactions'
    ]
    print("Successfully connected to send_pending MongoDB instance for Asia")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")


class DPoS:
    def __init__(self, sender_municipalities, receiver_municipalities):
        self.sender_municipalities = sender_municipalities
        self.receiver_municipalities = receiver_municipalities
        self.approved_representative = None

    def elect_representative(self, sender_or_receiver):
        if sender_or_receiver == 'sender':
            self.approved_representative = choice(self.sender_municipalities)
        elif sender_or_receiver == 'receiver':
            self.approved_representative = choice(self.receiver_municipalities)
        return self.approved_representative

    def approve_transaction(self, transaction):
        if self.approved_representative:
            transaction['signature'] = f"approved_by_{self.approved_representative}"
            return True
        return False


class ProofOfPlace:
    def __init__(self, location):
        self.location = location
        self.timestamp = datetime.now(pytz.utc)

    def generate_proof(self):
        hasher = hashlib.sha256()
        hasher.update(f"{self.location}{self.timestamp}".encode())
        return hasher.hexdigest()

    @staticmethod
    def verify_proof(proof, location, timestamp):
        hasher = hashlib.sha256()
        hasher.update(f"{location}{timestamp}".encode())
        return hasher.hexdigest() == proof


# 大陸名を抽出する関数（送信者用）
def determine_sender_continent(sender_municipality_data):
    try:
        # 'continent-city' の形式から大陸名を抽出
        continent = sender_municipality_data.split('-')[0]
        return continent
    except IndexError:
        return None


# 大陸名を抽出する関数（受信者用）
def determine_receiver_continent(receiver_municipality_data):
    try:
        # 'continent-city' の形式から大陸名を抽出
        continent = receiver_municipality_data.split('-')[0]
        return continent
    except IndexError:
        return None


# 送信者市町村名を抽出する関数
def determine_sender_municipality(sender_municipality_data):
    try:
        # 'continent-city' の形式から市町村名を抽出
        municipality = sender_municipality_data.split('-')[1]
        return municipality
    except IndexError:
        return "Unknown"  # フォーマットが異常な場合の対処


# 受信者市町村名を抽出する関数
def determine_receiver_municipality(receiver_municipality_data):
    try:
        # 'continent-city' の形式から市町村名を抽出
        municipality = receiver_municipality_data.split('-')[1]
        return municipality
    except IndexError:
        return "Unknown"  # フォーマットが異常な場合の対処


recent_transactions_lock = threading.Lock()


# 送信トランザクションの制限を確認する関数（1分以内に10件まで）
def check_recent_transactions():
    global recent_transactions
    current_time = datetime.now(timezone.utc)
    one_minute_ago = current_time - timedelta(minutes=1)

    with recent_transactions_lock:  # ロックで保護
        recent_transactions = [
            t for t in recent_transactions if t >= one_minute_ago
        ]
        if len(recent_transactions) >= 10:
            return False
        recent_transactions.append(current_time)
    return True


# 判断基準ロジック（最重要！）：ここが心臓部になるので、ここに微妙な判断事例を加えていくことで自動仕訳の精度があがる
def determine_accounts(transaction):
    criteria = {}

    # 判断基準に基づいた自動的な借方科目の設定
    if "長期的" in transaction["details"] or "価値創出" in transaction["details"]:
        debit_account = "愛貨再投資行動"  # Reinvestment of Love Tokens
        criteria["目的"] = "新たな価値創出を目指した長期的な投資としての行動"
        criteria["具体性"] = "個人の学習やスキルアップのための投資、またはプロジェクトへの協力"
    else:
        debit_account = "サポート行動の費用"  # Love Tokens Spent on Supporting Others
        criteria["目的"] = "他者の成長や成功を助けるための行動で、短期的サポート"
        criteria["具体性"] = "即座の支援やサポート、長期的な投資とは異なる直接的支援"

    # 貸方は一律で「愛貨」と設定
    credit_account = "愛貨"

    return debit_account, credit_account, criteria


# .env ファイルをロード
load_dotenv()


# ChatGPT API キーを設定
openai.api_key = os.getenv('OPENAI_API_KEY')


def fetch_ai_generated_journal_entry(transaction: Dict[str, Any]) -> str:
    """
    トランザクションデータからAIによる仕訳提案を生成
    """
    # プロンプトを生成
    prompt = f"""
    トランザクションの内容に基づき、適切な仕訳を生成してください。
    トランザクションID: {transaction['transaction_id']}
    日付: {datetime.now(timezone.utc).isoformat()}Z
    内容: {transaction}
    """

    # OpenAI API呼び出し
    try:
        response = openai.ChatCompletion.create(  # type: ignore
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは親切なAI会計士です。"},
                {"role": "user", "content": prompt}
            ]
        )

        # 応答の解析
        return response.choices[0].message["content"].strip()

    except Exception as e:
        raise RuntimeError(f"AIによる仕訳提案生成中にエラーが発生しました: {e}")


def generate_journal_entry(transaction):
    # AIによる初期仕訳提案の取得
    ai_suggested_entry = fetch_ai_generated_journal_entry(transaction)

    # 過去の仕訳例と比較し、最適な判断基準と仕訳を選択
    historical_judgments = {
        ("愛の行動消費", "愛貨"): {
            "purpose": "他者の成長や成功を助けるため",
            "expected_outcome": "直接の利益を求めずに感謝を伝える",
            "action_specificity": "即座の支援や一時的な協力",
            "duration": "短期的",
            "reciprocity": "直接的な見返りはない"
        },
        ("愛貨", "愛の行動受取"): {
            "purpose": "新たな価値創出を目指す長期的な投資",
            "expected_outcome": "将来の利益や価値創出",
            "action_specificity": "個人の学習やスキルアップ",
            "duration": "長期的",
            "reciprocity": "間接的な利益が期待される"
        }
    }

    # AI提案をパースし、仕訳の記録に使用するフィールドを設定
    # 例: {"debit": "愛の行動消費", "credit": "愛貨", "amount": 10, "criteria": {...}}
    ai_entry_data = json.loads(ai_suggested_entry)  # 返された文字列を辞書形式に変換

    # 過去の仕訳との一致を確認し、基準が一致する場合はそのまま、異なる場合はAIの基準を記録
    judgment_criteria = historical_judgments.get(
        (ai_entry_data['debit'], ai_entry_data['credit']),
        ai_entry_data.get("criteria")  # AIが新しい基準を生成した場合
    )

    # 仕訳エントリの作成
    journal_entry = JournalEntry(
        date=datetime.now(timezone.utc),
        sender=transaction['sender'],
        description=ai_entry_data.get(
            "description", "Auto-generated transaction"
        ),
        debit_account=ai_entry_data['debit'],
        credit_account=ai_entry_data['credit'],
        amount=transaction['amount'],
        judgment_criteria=judgment_criteria,
        transaction_id=transaction['transaction_id']
    )

    # journal_entry をデータベースへ保存
    save_journal_entry(journal_entry)

    return journal_entry


# MongoDBへ判断基準を保存する関数
def save_to_mongodb(entry, db_name, collection_name):
    mongo_uri = get_mongo_uri(db_name, entry.get('continent', 'Default'))
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]
    collection.insert_one(entry)


# 仕訳の保存・判断基準の比較と保存を行う関数
def save_journal_entry(journal_entry):
    journal_entry_dict = journal_entry.__dict__
    journal_entry_dict['debit_account_type'] = account_type_mapping.get(
        journal_entry.debit_account, "unknown"
    )
    journal_entry_dict['credit_account_type'] = account_type_mapping.get(
        journal_entry.credit_account, "unknown"
    )

    # 判断基準の保存部分
    ai_proposed_criteria = journal_entry_dict.get("criteria", {})
    historical_judgments = fetch_historical_judgments(
        journal_entry.debit_account,
        journal_entry.credit_account
    )

    selected_criteria, comparison_notes = compare_and_store_judgment(
        ai_proposed_criteria,
        historical_judgments
    )

    # MongoDBに保存
    continent = journal_entry_dict.get('continent', 'Default')
    journal_entry_dict['selected_criteria'] = selected_criteria  # 選択された基準を記録
    journal_entry_dict['comparison_notes'] = comparison_notes  # 比較結果も記録
    db = get_mongo_connection("journal_entries", continent)
    collection = db["journal_entries"]
    collection.insert_one(journal_entry_dict)

    print(
        f"Journal entry and criteria saved"
        f"for transaction {journal_entry.transaction_id}"
    )


# 過去の仕訳判断基準を取得する関数
def fetch_historical_judgments(debit_account, credit_account):
    db = get_mongo_connection("judgments_db", "Default")
    collection = db['historical_judgments']
    return list(collection.find({
        "debit_account": debit_account,
        "credit_account": credit_account
    }))


# AI提案と過去の判断基準を比較する関数
def compare_and_store_judgment(ai_proposed_criteria, historical_judgments):
    best_criteria = None
    comparison_notes = []

    # 過去の判断基準とAI提案の比較
    for historical_criteria in historical_judgments:
        differences = {}
        for key in ai_proposed_criteria:
            if (
                ai_proposed_criteria[key]
                != historical_criteria["criteria"].get(key)
            ):
                differences[key] = {
                    "AI_proposal": ai_proposed_criteria[key],
                    "historical": historical_criteria["criteria"].get(key)
                }

        comparison_notes.append({
            "compared_with": historical_criteria["_id"],
            "differences": differences,
            "reason_for_selection": "新しい基準の方が目的に合致する"
        })

        if not best_criteria or len(differences) < len(
            best_criteria["differences"]
        ):
            best_criteria = {
                "criteria": ai_proposed_criteria, "differences": differences
            }

    if best_criteria is None:
        raise ValueError("best_criteria is None, cannot access 'criteria'.")

    # 最終選択された基準を保存
    save_to_mongodb({
        "selected_criteria": best_criteria["criteria"],
        "comparison_notes": comparison_notes,
        "created_at": datetime.now(timezone.utc),
        "modified_at": datetime.now(timezone.utc)
    }, "judgments_db", "historical_judgments")

    return best_criteria["criteria"], comparison_notes


def record_evaluation_metrics(transaction):
    evaluation_entry = {
        "date": datetime.now(timezone.utc),
        "description": "Contribution to Joint Projects",
        "metric": "Contribution to Joint Projects with Love Tokens",
        "amount": transaction['amount'],
        "transaction_id": transaction['transaction_id']
    }
    mongo_uri = get_mongo_uri(
        "evaluation_metrics", transaction['sender_continent']
    )
    mongo_client = MongoClient(mongo_uri)
    mongo_collection = mongo_client['accounting_db']['evaluation_metrics']
    mongo_collection.insert_one(evaluation_entry)
    print(
        f"Evaluation metric recorded for transaction"
        f"{transaction['transaction_id']}"
    )


# MongoDB に保存する前にデータ検証を追加
def validate_transaction_data(data):
    required_fields = [
        'transaction_id', 'encrypted_data', 'signature', 'pq_public_key'
    ]
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"Missing or invalid field: {field}")


def save_transaction_to_mongodb(data, continent):
    validate_transaction_data(data)
    mongo_uri = get_mongo_uri("send_pending", continent)
    client = MongoClient(mongo_uri)
    db = client['transactions_db']
    collection = db['transactions']
    collection.insert_one(data)


#「ウォレット残高をMongoDBとimmuDB二重管理する」ための関数を作成する
def get_wallet_balance_both(user_id: str) -> float:
    """
    MongoDB側とimmuDB側のウォレット残高を取得し、
    たとえば「大きい方を返す」などの方針で値を返す例。
    """
    # MongoDB 側
    mongo_doc = wallet_collection.find_one({"user_id": user_id})
    mongo_balance = 0.0
    if mongo_doc and "balance" in mongo_doc:
        mongo_balance = float(mongo_doc["balance"])

    # immuDB 側
    immu_balance = get_wallet_from_immudb(user_id)  # 新規追加関数

    # ここでは、例として「大きい方を採用する」
    return max(mongo_balance, immu_balance)


def update_wallet_balance_both(user_id: str, amount: float):
    """
    MongoDBとimmuDBの両方を更新する。
    すでにある残高に amount を加算する (負の場合は減算)。
    """
    # まずMongoDBを更新
    existing = wallet_collection.find_one({"user_id": user_id})
    if not existing:
        wallet_collection.insert_one({"user_id": user_id, "balance": amount})
        new_mongo_balance = amount
    else:
        new_mongo_balance = existing["balance"] + amount
        if new_mongo_balance < 0:
            new_mongo_balance = 0
        wallet_collection.update_one(
            {"user_id": user_id},
            {"$set": {"balance": new_mongo_balance}}
        )

    # immuDB も更新
    update_wallet_in_immudb(user_id, amount)
    new_immu_balance = get_wallet_from_immudb(user_id)

    print(f"[Both] user={user_id}, mongo_balance={new_mongo_balance}, immu_balance={new_immu_balance}")


@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    data = request.json
    user_id = data.get("user_id")
    initial_balance = data.get("initial_balance", 0.0)

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    # 2重管理
    update_wallet_balance_both(user_id, initial_balance)
    print(f"Wallet created (both DBs) for {user_id} with {initial_balance}")
    return jsonify({"message": "Wallet created successfully"}), 200


@app.route('/get_balance', methods=['GET'])
def get_balance():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    # 2重管理: 両方の残高を取得
    final_balance = get_wallet_balance_both(user_id)
    return jsonify({"user_id": user_id, "balance": final_balance}), 200


def get_wallet_balance_from_municipal_chain(wallet_address):
    # municipal_chain の API にリクエストを送信して残高を取得
    url = f"http://localhost:8000/get_balance/{wallet_address}"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json().get('balance', 0)
    else:
        return 0


# ウォレット残高を取得
wallet_address = "0xABCDEF1234567890"
balance = get_wallet_balance_from_municipal_chain(wallet_address)
print(f"Wallet {wallet_address} has a balance of {balance}")


@app.route('/send_funds', methods=['POST'])
def send_funds():
    data = request.json
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    amount = data.get('amount')

    if not sender_id or not receiver_id or amount is None:
        return jsonify({"error": "Missing sender_id, receiver_id or amount"}), 400

    # 2重管理: 両方の残高を取得
    sender_balance = get_wallet_balance_both(sender_id)
    receiver_balance = get_wallet_balance_both(receiver_id)

    if sender_balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    # senderから引き、receiverに足す
    update_wallet_balance_both(sender_id, -amount)
    update_wallet_balance_both(receiver_id, amount)

    # トランザクションの作成
    transaction = {
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "amount": amount,
        "status": "pending",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "transaction_id": str(uuid.uuid4())
    }

    # municipal_chainへのURLは既存の仕組みに合わせて取得
    # municipal_chain_url = determine_municipal_chain(sender_id, receiver_id)
    municipal_chain_url = determine_municipal_chain(sender_id, receiver_id)

    if not municipal_chain_url:
        return jsonify(
            {"error": "Could not determine municipal chain URL"}
        ), 500

    # Municipal Chainへ送信 (POST)
    response = requests.post(
        f"{municipal_chain_url}/approve_transaction", json=transaction
    )

    if response.status_code == 200:
        # 成功応答の場合
        return jsonify(
            {"message": "Transaction submitted", "transaction": transaction}
        ), 200
    else:
        return jsonify({"error": "Transaction submission failed"}), 500


@app.route('/generate_keys', methods=['GET'])
def generate_keys_route():
    """公開鍵と秘密鍵を生成し、それを返すエンドポイント"""
    global ntru_instance
    ntru_instance = Ntru(N_new=11, p_new=3, q_new=128)
    f_new = [1, -1, 0, 1]  # 鍵生成用の秘密鍵成分
    g_new = [0, 1, -1, 1]
    d_new = 7

    try:
        ntru_instance.genPublicKey(f_new, g_new, d_new)
        public_key = ntru_instance.getPublicKey()
        private_key = f_new  # 秘密鍵としてf_newを利用
        return jsonify(
            {"public_key": public_key, "private_key": private_key}
        ), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/encrypt', methods=['POST'])
def encrypt_route():
    """暗号化を行うエンドポイント"""
    global ntru_instance
    if ntru_instance is None:
        return jsonify({"error": "鍵が生成されていません。"}), 400

    data = request.json
    if not data:
        return jsonify({"error": "リクエストデータが空です。"}), 400
    # message は list[int]を想定 (もしくは文字列をintに変換)
    message_poly = data.get('message_poly')  # ex: [0,1,0, -1, ...]
    rand_poly = data.get('rand_poly')        # ex: [1, -1, 0, ...]
    message = data.get("message")
    public_key = data.get("public_key")

    if not message or not public_key:
        return jsonify({"error": "無効な入力データです。"}), 400

    try:
        ciphertext = ntru_instance.encrypt(message_poly, rand_poly)
        return jsonify({"ciphertext": ciphertext}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/decrypt', methods=['POST'])
def decrypt_route():
    """復号化を行うエンドポイント"""
    global ntru_instance
    if ntru_instance is None:
        return jsonify({"error": "鍵が生成されていません。"}), 400

    data = request.json
    if not data:
        return jsonify({"error": "リクエストデータが空です。"}), 400
    
    enc_poly = data.get('encrypted_poly')  # [100, 200, ...]
    encrypted_message = data.get("encrypted_message")
    private_key = data.get("private_key")

    if not encrypted_message or not private_key:
        return jsonify({"error": "無効な入力データです。"}), 400
    
    try:
        plaintext_poly = ntru_instance.decrypt(enc_poly)
        # plaintext_poly を文字列に変換する等の処理
        return jsonify({"plaintext_poly": plaintext_poly}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/process', methods=['POST'])
def process_transaction():
    data = request.json

    # 必要なインスタンスを初期化
    try:
        from ntru import Ntru
        ntru_instance = Ntru(N_new=7, p_new=3, q_new=491531)
    except ImportError as e:
        return jsonify({"error": "Failed to import Ntru: " + str(e)}), 500

    # データがNoneの場合、エラーを返す
    if data is None:
        return jsonify({"error": "No data received"}), 400

    # 必須フィールドの検証
    required_fields = [
        'sender', 'sender_municipality',
        'receiver', 'receiver_municipality', 'amount'
    ]
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify(
                {"error": f"Missing or invalid field: {field}"}
            ), 400

    # 残高確認
    user_id = data['sender']
    balance_res = requests.get(
        f"{MUNICIPAL_CHAIN_URL}/get_balance?user_id={user_id}"
    )
    if balance_res.status_code != 200:
        return jsonify({"error": "Failed to fetch sender balance"}), 500

    balance_data = balance_res.json()
    sender_balance = float(balance_data['balance'])
    if sender_balance < float(data['amount']):
        return jsonify({"error": "Insufficient balance"}), 400

    # 十分な残高があれば暗号化と送信処理続行...
    # amountの型検証（正の浮動小数点数）
    try:
        data['amount'] = float(data['amount'])
        if data['amount'] <= 0:
            raise ValueError("Amount must be a positive number.")
    except ValueError:
        return jsonify(
            {"error": "Invalid amount. Must be a positive number."}
        ), 400

    # 市町村と大陸情報を取得
    sender_municipalities = [data['sender_municipality']]
    receiver_municipalities = [data['receiver_municipality']]
    sender_continent = determine_sender_continent(
        data['sender_municipality']
    )
    receiver_continent = determine_receiver_continent(
        data['receiver_municipality']
    )
    data['sender_continent'] = sender_continent
    data['receiver_continent'] = receiver_continent

    # DPoS で代表者を選出
    dpos = DPoS(sender_municipalities, receiver_municipalities)
    sender_rep = dpos.elect_representative('sender')
    receiver_rep = dpos.elect_representative('receiver')

    # トランザクションの準備
    transaction = {
        'sender': data['sender'],
        'receiver': data['receiver'],
        'from_wallet': data['from_wallet'],
        'to_wallet': data['to_wallet'],
        'amount': data['amount'],
        'sender_municipality': data['sender_municipality'],
        'receiver_municipality': data['receiver_municipality'],
        'sender_continent': data['sender_continent'],
        'receiver_continent': data['receiver_continent'],
        'timestamp': datetime.now(timezone.utc).isoformat() + "Z",
        'transaction_id': str(uuid.uuid4()),
        'status': 'pending'
    }

    # トランザクションデータを JSON バイト列に変換
    transaction_data_json = json.dumps(transaction, sort_keys=True).encode(
        'utf-8'
    )

    # 暗号化と署名の処理
    try:
        # NTRU 暗号化
        encrypted_data = encrypt_transaction_data(
            transaction_data_json.decode('utf-8'), ntru_instance
        )
        transaction['encrypted_data'] = encrypted_data

        # Dilithium 署名
        signature = generate_signature(transaction_data_json, pq_private_key)
        transaction['signature'] = signature
        transaction['pq_public_key'] = pq_public_key.hex()  # 公開鍵を追加
    except Exception as e:
        return jsonify(
            {"error": f"Encryption or signature failed: {str(e)}"}
        ), 500

    # トランザクションの承認
    if dpos.approve_transaction(transaction):
        # MongoDBに保存
        try:
            mongo_uri = get_mongo_uri(
                "send_pending", transaction['sender_continent']
            )
            mongo_client = MongoClient(mongo_uri)
            mongo_collection = mongo_client['transactions_db']['transactions']
            mongo_collection.insert_one(transaction)
            print("Transaction saved successfully.")
        except Exception as e:
            print(f"Failed to save transaction: {str(e)}")
            return jsonify(
                {"error": "Failed to save transaction to database."}
            ), 500

        return jsonify(
            {"status": "Transaction approved", "transaction": transaction}
        ), 200
    else:
        return jsonify({"error": "Transaction approval failed."}), 500


# ProofOfPlaceの生成と検証を動的に行う関数
def generate_and_verify_proof(location):
    # 動的に現在のタイムスタンプを使ってProofOfPlaceを生成
    proof_of_place = ProofOfPlace(location=location)
    generated_proof = proof_of_place.generate_proof()

    # タイムスタンプと場所を使って生成された証明を検証
    is_valid = ProofOfPlace.verify_proof(
        generated_proof, location, proof_of_place.timestamp
    )

    print(f"Generated proof: {generated_proof}")
    print(f"Proof is valid: {is_valid}")
    return generated_proof, is_valid


def get_sender_keys():
    """
    送信者の鍵を取得する。
    初期化済みの Dilithium 鍵ペア (pq_private_key, pq_public_key) を返します。
    """
    global pq_private_key, pq_public_key
    if pq_private_key is None or pq_public_key is None:
        raise ValueError(
            "Sender keys are not initialized. Please initialize them first."
        )
    return pq_private_key, pq_public_key


def create_signature(message: bytes, pq_private_key: bytes) -> str:
    """
    指定されたメッセージに対して秘密鍵を使用して署名を作成します。

    Args:
        message (bytes): 署名するメッセージ (バイト列)。
        pq_private_key (bytes): Dilithium の秘密鍵。

    Returns:
        str: 署名データ (16進文字列)。
    """
    try:
        # メッセージに署名を付与
        signature = generate_signature(message, pq_private_key)
        return signature.hex()  # 署名データを16進文字列に変換して返す
    except Exception as e:
        raise ValueError(f"Failed to create signature: {str(e)}")


# dilithium秘密鍵で署名
def generate_signature(transaction_data, private_key):
    try:
        return dilithium_instance.generate_signature(
            private_key, transaction_data
        )
    except Exception as e:
        raise ValueError(f"Failed to generate signature: {str(e)}")


# 公開鍵を使用して署名の正当性をチェック
def verify_signature(transaction_data, signature):
    """署名の検証"""
    global pq_public_key
    try:
        return dilithium_instance.verify_signature(
            pq_public_key, transaction_data, signature
        )
    except Exception as e:
        raise ValueError(f"Signature verification failed: {str(e)}")


# 復号化処理(ntru_encryption)
def decrypt_transaction_data(encrypted_data, private_key):
    # NTRUインスタンスを初期化
    ntru = Ntru(N_new=11, p_new=3, q_new=32)  # 同じパラメータで初期化
    ntru.f = private_key  # 秘密鍵を設定

    # 復号化
    decrypted_message = ntru.decrypt(encrypted_data)

    # 数値リストを文字列に変換
    decrypted_data = ''.join(chr(num) for num in decrypted_message)
    return decrypted_data


@app.route('/create_transaction', methods=['POST'])
def create_transaction():
    data = request.get_json()  # リクエストデータを取得

    # リクエストデータが存在しない場合
    if not data:
        return jsonify({"error": "Invalid JSON or no data received"}), 400

    # 必要なフィールドを確認
    required_fields = [
        'sender', 'receiver', 'amount', 'sender_municipality',
        'receiver_municipality', 'continent'
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # attributesフィールドを取得（デフォルトは空の辞書）
    attributes = data.get('attributes', {})
    if not isinstance(attributes, dict):
        return jsonify(
            {"error": "Invalid attributes format. Must be a JSON object."}
        ), 400

    # 大陸情報を抽出
    sender_continent = determine_sender_continent(
        data['sender_municipality']
    )
    receiver_continent = determine_receiver_continent(
        data['receiver_municipality']
    )

    # トランザクションデータの準備, JSONデータをバイト列に変換
    transaction_data = json.dumps(data, sort_keys=True).encode('utf-8')

    # トランザクションデータに署名を作成
    try:
        signature = generate_signature(transaction_data)
        data['signature'] = signature.hex()  # 署名を16進文字列に変換して保存
    except ValueError as e:
        return jsonify({"error": str(e)}), 500

    # 署名の検証
    try:
        if not verify_signature(transaction_data, bytes.fromhex(signature)):
            return jsonify({"error": "Invalid signature"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 500

    # たとえば: イベントとして "transaction_id" と "timestamp" を使う
    transaction_id = str(uuid.uuid4())
    current_ts_str = datetime.now(timezone.utc).isoformat() + "Z"
    
    # PoHへの追加
    global poh
    poh.add_event(event_data=transaction_id, event_timestamp=current_ts_str)

    # トランザクションデータの整形
    transaction = {
        "sender": data.get('sender', ''),
        "receiver": data.get('receiver', ''),
        "to_wallet": data.get('receiver', ''),
        "from_wallet": data.get('receiver', ''),
        "amount": float(data.get('amount', 0)),
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "transaction_id": str(uuid.uuid4()),
        "verifiable_credential": data.get('verifiable_credential', ''),
        "signature": signature_hex,  # 署名を追加
        "pq_public_key": pq_public_key.hex(),  # 公開鍵を追加
        "subject": data.get('subject', ''),
        "action_level": data.get('action_level', ''),
        "dimension": data.get('dimension', ''),
        "fluctuation": data.get('fluctuation', ''),
        "organism_name": data.get('organism_name', ''),
        "sender_municipality": data.get('sender_municipality', ''),
        "receiver_municipality": data.get('receiver_municipality', ''),
        "sender_municipal_id": data.get('sender_municipality', ''),
        "receiver_municipal_id": data.get('receiver_municipality', ''),
        "details": data.get('details', ''),
        "goods_or_money": data.get('goods_or_money', ''),
        "location": data.get('location', ''),
        "proof_of_place": data.get('proof_of_place', ''),
        "status": "send_pending",  # 初期ステータスを設定
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",  # 作成日時を追加
        "attributes": attributes,  # 新しく追加
    }

    # ここで仕訳を生成
    journal_entry = generate_journal_entry(transaction)

    # 仕訳をデータベースに保存
    save_journal_entry(journal_entry)

    # 評価項目の記録
    record_evaluation_metrics(transaction)

    # DPoSのインスタンスを作成し、送信者と受信者の代表者を選出
    sender_municipalities = [data.get('sender_municipality', '')]
    receiver_municipalities = [data.get('receiver_municipality', '')]
    dpos = DPoS(
        sender_municipalities, receiver_municipalities
    )
    sender_rep = dpos.elect_representative('sender')
    receiver_rep = dpos.elect_representative('receiver')

    # トランザクションの承認
    if dpos.approve_transaction(transaction):
        # MongoDBコレクションに接続
        mongo_uri = get_mongo_uri(
            "send_pending", transaction['sender_continent']
        )
        mongo_client = MongoClient(mongo_uri)
        mongo_collection = mongo_client['transactions_db']['transactions']

        # トランザクションを挿入
        try:
            mongo_collection.insert_one(transaction)
            print(
                "Transaction inserted successfully with status 'send_pending'"
            )
        except Exception as e:
            print(f"Failed to insert transaction: {e}")
            return jsonify({"error": "Failed to insert transaction"}), 500

        # 送信先のMunicipal Chainにトランザクションを送信
        municipal_chain_url = determine_municipal_chain(
            transaction['sender_municipality'],
            transaction['receiver_municipality']
        )
        print(f"Sending to Municipal Chain URL: {municipal_chain_url}")

        try:
            response = requests.post(
                f'{municipal_chain_url}/receive_transaction', json=transaction
            )

            if response.status_code == 200:
                print("Transaction sent successfully to Municipal Chain")
                return jsonify({"status": "success"}), 200
            else:
                print(f"Failed to send transaction: {response.text}")
                return jsonify(
                    {"error": "Failed to send transaction"}
                ), response.status_code

        except requests.exceptions.RequestException as e:
            print(f"Error occurred: {str(e)}")
            return jsonify({"error": str(e)}), 500  # エラー時の処理
    else:
        return jsonify({"error": "Failed to approve transaction"}), 500


@app.route('/poh', methods=['GET'])
def get_poh_state():
    """
    現在のPoH (Proof of History) 状態を返すエンドポイント。
    """
    global poh
    latest_hash = poh.get_latest_hash()
    sequence_list = poh.get_sequence_list()

    return jsonify({
        "latest_hash": latest_hash,
        "event_count": len(poh),
        "sequence": sequence_list
    }), 200


# 署名を検証・複合化する
@app.route('/receive_transaction', methods=['POST'])
def receive_transaction():
    data = request.get_json()

    # 入力データのバリデーション
    if not data or 'transaction_id' not in data:
        return jsonify(
            {"error": "Invalid transaction data. 'transaction_id' is missing."}
        ), 400

    # MongoDBからトランザクションを取得
    mongo_client = MongoClient(get_mongo_uri("transactions", "Default"))
    mongo_collection = mongo_client['transactions_db']['transactions']
    transaction = mongo_collection.find_one(
        {"transaction_id": data['transaction_id']}
    )

    if not transaction:
        return jsonify(
            {"error": (
                f"Transaction with ID {data['transaction_id']} not found."
            )}
        ), 404

    # 必要なフィールドの取得
    encrypted_data_base64 = transaction.get("encrypted_data")
    pq_signature_hex = transaction.get("signature")
    pq_public_key_hex = transaction.get("pq_public_key")
    ntru_private_key_hex = data.get("ntru_private_key")  # リクエストから秘密鍵を受け取る

    # 必須データの確認
    if (
        not encrypted_data_base64 or
        not pq_signature_hex or
        not pq_public_key_hex or
        not ntru_private_key_hex
    ):
        return jsonify({
            "error": (
                "Missing required data: "
                "encrypted_data, signature, public_key, or ntru_private_key."
            )
        }), 400

    # 復号化処理
    try:
        # 秘密鍵を16進文字列からバイト列に変換
        ntru_private_key = bytes.fromhex(ntru_private_key_hex)

        # 暗号化データをBase64からデコードし、16進文字列に変換
        encrypted_data_hex = base64.b64decode(encrypted_data_base64).hex()

        # 復号化
        decrypted_data = decrypt_transaction_data(
            encrypted_data_hex, ntru_private_key_hex
        )
        transaction_data = json.loads(decrypted_data)  # 復号化されたデータをJSONに変換
    except Exception as e:
        return jsonify({"error": f"Decryption failed: {str(e)}"}), 500

    # dilithium署名検証
    try:
        pq_signature = bytes.fromhex(pq_signature_hex)  # 署名を16進文字列からバイト列に変換
        pq_public_key = bytes.fromhex(pq_public_key_hex)  # 公開鍵を16進文字列からバイト列に変換
        # 復号化
        decrypted_data = decrypt_transaction_data(
            encrypted_data_base64, ntru_private_key
        )
        transaction_data = json.loads(decrypted_data)

        # 署名検証
        if not verify_signature(
            transaction_data, pq_signature_hex, pq_public_key_hex
        ):
            return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        return jsonify(
            {"error": f"Decryption or signature verification failed: {str(e)}"}
        ), 500

    # トランザクションが正常に処理された場合
    return jsonify({
        "transaction": transaction_data,
        "status": "Transaction verified and decrypted successfully"
    }), 200


@app.route('/verify_transaction', methods=['POST'])
def verify_transaction():
    data = request.get_json()

    transaction_data = json.dumps(data['transaction']).encode('utf-8')
    signature = bytes.fromhex(data['signature'])
    pq_public_key = bytes.fromhex(data['pq_public_key'])

    # 検証結果を返す
    try:
        is_valid = verify_signature(
            transaction_data, signature, pq_public_key
        )
        return jsonify({"is_valid": is_valid}), 200
    except Exception as e:
        return jsonify(
            {"error": f"Signature verification failed: {str(e)}"}
        ), 500


@app.route('/add_block', methods=['POST'])
def add_block():
    data = request.json

    # data が None かどうかを確認
    if data is None:
        return jsonify({"error": "No data received"}), 400

    # 送信者と受信者の市町村情報を取得
    sender_municipality = data.get('sender_municipality', '')
    receiver_municipality = data.get('receiver_municipality', '')

    # 市町村に基づいて動的に Municipal Chain の URL を決定
    municipal_chain_url = determine_municipal_chain(
        sender_municipality, receiver_municipality
    )

    # Municipal Chain にデータを送信
    try:
        response = requests.post(f'{municipal_chain_url}/add_block', json=data)
        response.raise_for_status()  # HTTPエラーステータスコードをチェック

        # レスポンスを JSON 形式で返す
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        # エラーメッセージを出力してエラーレスポンスを返す
        print(
            f"Error occurred while sending data to Municipal Chain: {str(e)}"
        )
        return jsonify(
            {"error": "Failed to send data to Municipal Chain"}
        ), 500


def poh_continuous_update():
    """
    一定間隔で PoH にダミーイベントを追加し、
    PoHを進行させ続けるスレッド用の関数。
    """
    global poh
    while True:
        time.sleep(1.0)  # 1秒おき
        now_str = datetime.now(timezone.utc).isoformat() + "Z"
        # "tick" などダミー文字列を入れる
        poh.add_event(event_data="tick", event_timestamp=now_str)
        print(
            f"[PoH Thread] tick added -> latest_hash={poh.get_latest_hash()}"
        )


# アプリケーション開始時にスレッドを開始
poh_thread = threading.Thread(target=poh_continuous_update, daemon=True)
poh_thread.start()


# BASE_DIR の定義
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# グローバル変数 municipalities_data の初期化
municipalities_data = {}

# municipalities_data.json の読み込み
municipalities_file_path = os.path.join(BASE_DIR, 'municipalities.json')

# ファイルが存在するか確認
if not os.path.exists(municipalities_file_path):
    raise FileNotFoundError(
        f"Error: '{municipalities_file_path}' not found. "
        "Please check the path."
    )

# ファイルを開くときにエラーハンドリングを追加
try:
    with open(municipalities_file_path, 'r', encoding='utf-8') as file:
        municipalities_data = json.load(file)
except json.JSONDecodeError as e:
    raise ValueError(
        f"Error decoding JSON from '{municipalities_file_path}': {e}"
    )
except Exception as e:
    raise RuntimeError(
        f"An error occurred while reading '{municipalities_file_path}': {e}"
    )


# municipalities_data をグローバルに設定
def initialize_globals():
    global municipalities_data
    return municipalities_data


# 関数内でグローバル変数を使う
def determine_municipal_chain(sender_municipality, receiver_municipality):
    global municipalities_data  # グローバル変数を参照する

    # 市町村の URL を保存するための辞書を初期化
    municipal_chain_urls = {}

    # 大陸ごとの市町村情報をループしてURLを設定
    for continent, continent_data in municipalities_data.items():
        for city_data in continent_data.get('cities', []):
            # cities データから各市町村のURLを構築
            city_name = city_data['name']
            city_port = city_data.get('city_port')  # 必要な場合にアクセス
            if city_port:  # city_portが存在する場合にURLを設定
                key = f"{continent}-{city_name}"
                url = f"http://127.0.0.1:{city_port}"
                municipal_chain_urls[key] = url

    # 送信者または受信者の市町村に基づいて Municipal Chain の URL を選択
    if sender_municipality in municipal_chain_urls:
        return municipal_chain_urls[sender_municipality]
    elif receiver_municipality in municipal_chain_urls:
        return municipal_chain_urls[receiver_municipality]
    else:
        # 市町村が見つからない場合のデフォルト処理を追加
        default_city = municipalities_data['Default']['cities'][0]
        default_city_port = default_city['city_port']
        default_url = f"http://127.0.0.1:{default_city_port}"
        sender_url = municipal_chain_urls.get(sender_municipality)
        receiver_url = municipal_chain_urls.get(receiver_municipality)

        # sender_url, receiver_url のいずれかが存在しない場合、default_url を返す
        return sender_url or receiver_url or default_url


def determine_continental_chain_url(continent, municipality):
    global municipalities_data  # グローバル変数を参照する

    def build_url(flask_port):
        """
        指定されたポート番号を使って完全なURLを構築するヘルパー関数
        """
        base_url = "http://localhost"
        endpoint = "/continental_main_chain_endpoint"
        return f"{base_url}:{flask_port}{endpoint}"

    # 大陸ごとのContinental Main Chainのデータを取得する
    continent_data = municipalities_data.get(continent, {})

    # 大陸のデフォルトflask_portを取得
    base_flask_port = continent_data.get(
        'flask_port', municipalities_data['Default']['flask_port']
    )

    # 市町村に基づいてURLを構築する
    for city_data in continent_data.get('cities', []):
        if city_data['name'] == municipality:
            # 市町村固有のflask_portを優先的に使用
            city_flask_port = city_data.get('city_flask_port', base_flask_port)
            return build_url(city_flask_port)

    # 市町村が見つからなかった場合、デフォルトのflask_portを使用
    return build_url(base_flask_port)


@app.route('/api/financial_statements')
@jwt_required()
def financial_statements():
    # 認証済みユーザーを取得
    current_user = get_jwt_identity()

    # リクエストから市町村名を取得
    municipality_name = request.args.get('municipality', 'DefaultCity')

    # 市町村名から大陸名を取得する関数を使用
    current_continent = get_continent_from_municipality(municipality_name)

    # MongoDBに接続
    mongo_uri = get_mongo_uri("journal_entries", current_continent)
    mongo_client = MongoClient(mongo_uri)

    # データベース名を取得（URIの最後の部分）
    db_name = mongo_uri.rsplit('/', 1)[-1]
    mongo_db = mongo_client[db_name]

    # コレクションを取得
    journal_entries_collection = mongo_db['journal_entries']

    # 現在の日付
    today = datetime.now(timezone.utc)

    # 科目タイプごとに金額を集計
    pipeline = [
        # 借方科目の集計
        {
            "$group": {
                "_id": {
                    "account_type": "$debit_account_type"
                },
                "total_debit": {"$sum": "$amount"}
            }
        },
        # 貸方科目の集計をマージ
        {
            "$unionWith": {
                "coll": "journal_entries",
                "pipeline": [
                    {
                        "$group": {
                            "_id": {
                                "account_type": "$credit_account_type"
                            },
                            "total_credit": {"$sum": "$amount"}
                        }
                    }
                ]
            }
        }
    ]

    aggregated_data = list(journal_entries_collection.aggregate(pipeline))

    # 科目タイプごとにデータを整理
    financial_data = {
        "assets": 0.0,
        "liabilities": 0.0,
        "equity": 0.0,
        "revenue": 0.0,
        "expenses": 0.0,
        "net_profit": 0.0
    }

    for data in aggregated_data:
        account_type = data['_id'].get('account_type', 'unknown')
        total_debit = data.get('total_debit', 0.0)
        total_credit = data.get('total_credit', 0.0)

        if account_type in financial_data:
            financial_data[account_type] += total_debit - total_credit

    # 純利益の計算
    # ネット利益を計算
    financial_data['net_profit'] = (
        financial_data['revenue']
        - financial_data['expenses']
    )

    # JSON形式でデータを返す
    return jsonify({
        "date": today.strftime('%Y-%m-%d'),
        "financial_data": financial_data
    })


@app.route('/generate_proof_of_place', methods=['POST'])
def generate_proof_of_place():
    try:
        data = request.get_json(force=True)  # JSONデータを強制的に取得
        proof_of_place = ProofOfPlace(
            location=(data['latitude'], data['longitude'])
        )
        proof = proof_of_place.generate_proof()
        return jsonify(
            {"proof": proof, "timestamp": proof_of_place.timestamp.isoformat()}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/verify_proof_of_place', methods=['POST'])
def verify_proof_of_place():
    try:
        data = request.get_json(force=True)  # JSONデータを強制的に取得
        proof = data['proof']
        location = (data['latitude'], data['longitude'])
        timestamp = datetime.fromisoformat(data['timestamp'])
        is_valid = ProofOfPlace.verify_proof(proof, location, timestamp)
        return jsonify({"is_valid": is_valid})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Municipal Chainへのトランザクション送信を行うエンドポイント
@app.route('/send', methods=['POST'])
def send_love_currency():
    global recent_transactions
    data = request.json  # フロントエンドからのデータを受け取る

    # dataがNoneの場合エラーを返す
    if data is None:
        return jsonify({"error": "Invalid input data"}), 400

    # トランザクション数を確認（1分以内に10件以上ならエラー）
    if not check_recent_transactions():
        return jsonify(
            {
                "error": (
                    "Too many transactions in the last minute. "
                    "Please try again later."
                )
            }
        ), 429

    # 必須フィールドの確認
    required_fields = [
        'sender',
        'receiver',
        'amount',
        'sender_municipality',
        'receiver_municipality',
        'ntru_public_key',
        'pq_private_key',
    ]

    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # データの準備
    sender_continent = determine_sender_continent(data['sender_municipality'])
    receiver_continent = determine_receiver_continent(
        data['receiver_municipality']
    )

    # amount を float に変換
    try:
        data['amount'] = float(data['amount'])
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400

    # 公開鍵と秘密鍵を取得
    try:
        # 16進文字列からバイト列に変換
        ntru_public_key = bytes.fromhex(data['ntru_public_key'])
        pq_private_key = bytes.fromhex(data['pq_private_key'])
    except ValueError:
        return jsonify({"error": "Invalid key format"}), 400

    # トランザクションデータの追加フィールド
    data.update({
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "transaction_id": str(uuid.uuid4()),
        "status": "send",
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        "sender_continent": sender_continent,
        "receiver_continent": receiver_continent,
        "sender_municipal_id": data['sender_municipality'],
        "receiver_municipal_id": data['receiver_municipality']
    })

    # 暗号化処理
    try:
        # データをバイト列に変換
        transaction_data = json.dumps(data, sort_keys=True).encode('utf-8')
        encrypted_data = encrypt_with_ntru(transaction_data, ntru_public_key)

        # 型確認と変換
        if isinstance(encrypted_data, bytes):
            data['encrypted_data'] = encrypted_data.hex()  # バイト列から16進文字列に変換
        elif isinstance(encrypted_data, str):
            # 暗号化データが文字列の場合、そのまま格納
            data['encrypted_data'] = encrypted_data
        else:
            raise ValueError(
                f"Unexpected encrypted_data type: {type(encrypted_data)}"
            )
    except Exception as e:
        return jsonify({"error": f"Encryption failed: {str(e)}"}), 500

    # 署名生成
    try:
        # バイト列として署名を生成
        signature = sign_with_dilithium(transaction_data, pq_private_key)
        data['signature'] = signature.hex()  # 署名を16進文字列に変換して保存
    except Exception as e:
        return jsonify(
            {"error": f"Signature generation failed: {str(e)}"}
        ), 500

    # トランザクションをMongoDBに保存
    try:
        mongo_uri = get_mongo_uri("send", sender_continent)
        mongo_client = MongoClient(mongo_uri)
        mongo_collection = mongo_client['transactions_db']['transactions']
        mongo_collection.insert_one(data)
        print("Transaction inserted successfully with status 'send'")
    except Exception as e:
        print(f"Failed to insert transaction: {e}")
        return jsonify({"error": "Failed to insert transaction"}), 500

    # Municipal Chainにトランザクションを送信
    sender_municipality = data['sender_municipality']
    receiver_municipality = data['receiver_municipality']
    municipal_chain_url = determine_municipal_chain(
        sender_municipality, receiver_municipality
    )

    try:
        response = requests.post(
            f'{municipal_chain_url}/receive_transaction', json=data
        )
        if response.status_code == 200:
            print("Transaction sent successfully to Municipal Chain")

            # 承認されたらステータスを "send_pending" に更新
            mongo_collection.update_one(
                {"transaction_id": data['transaction_id']},
                {"$set": {"status": "send_pending"}}
            )
            return jsonify({"status": "success"}), 200
        else:
            print(f"Failed to send transaction: {response.text}")
            return jsonify(
                {"error": "Failed to send transaction"}
            ), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while sending to Municipal Chain: {e}")
        return jsonify({"error": str(e)}), 500


# ルートエンドポイント
@app.route('/')
def index():
    return financial_statements()


def home():
    return "Flask app is running!"


@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()

    if data is None:
        return jsonify({"error": "No data received"}), 400

    # 必要なフィールドを確認
    required_fields = ['transaction_id', 'new_status', 'sender_municipal_id']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    transaction_id = data['transaction_id']
    new_status = data['new_status']
    sender_municipal_id = data['sender_municipal_id']

    # sender_municipal_id から大陸名を取得
    sender_continent = determine_sender_continent(sender_municipal_id)
    if not sender_continent:
        sender_continent = 'Default'

    try:
        # MongoDBコレクションに接続（send_pending）
        mongo_uri = get_mongo_uri("send_pending", sender_continent)
        mongo_client = MongoClient(mongo_uri)
        mongo_collection = mongo_client['transactions_db']['transactions']

        # トランザクションを更新
        # クエリ条件を変数に格納
        query_filter = {
            "transaction_id": transaction_id,
            "sender_municipal_id": sender_municipal_id,
        }

        # 更新データを変数に格納
        update_data = {
            "$set": {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat() + "Z",
            },
        }

        # update_oneの呼び出し
        result = mongo_collection.update_one(query_filter, update_data)

        if result.matched_count == 0:
            return jsonify({"error": "Transaction not found"}), 404

        print(f"Transaction {transaction_id} updated to status {new_status}")

        # ステータスが "complete" の場合、分析用データベースに移行
        if new_status == "complete":
            transaction = mongo_collection.find_one(
                {"transaction_id": transaction_id}
            )
            if transaction:
                # 分析用 MongoDB に接続
                analytics_uri = get_mongo_uri("analytics", sender_continent)
                analytics_client = MongoClient(analytics_uri)
                analytics_collection = (
                    analytics_client['analytics_db']['transactions']
                )

                # トランザクションを挿入
                analytics_collection.insert_one(transaction)
                print(
                    f"Transaction {transaction_id} migrated to "
                    "analytics database."
                )

                # 元のトランザクションを削除
                mongo_collection.delete_one({"transaction_id": transaction_id})

        return jsonify({"status": "Transaction updated"}), 200
    except Exception as e:
        print(f"Failed to update transaction: {e}")
        return jsonify({"error": "Failed to update transaction"}), 500


@app.route('/api/send_transaction', methods=['POST'])
@jwt_required()  # トークン認証が必要
def send_transaction():
    current_user = get_jwt_identity()  # 現在の認証済みユーザーを取得
    data = request.get_json()  # リクエストデータをJSON形式で取得

    # 必要なフィールドを確認
    required_fields = [
        'sender',
        'receiver',
        'amount',
        'sender_municipality',
        'receiver_municipality',
        'pq_private_key',
        'seed_phrase',
    ]
    for field in required_fields:
        if field not in data or data[field] is None:
            return jsonify(
                {"error": f"Missing or invalid field: {field}"}
            ), 400

    # 市町村のデータを取得
    sender_municipalities = [data['sender_municipality']]
    receiver_municipalities = [data['receiver_municipality']]

    # 大陸情報を抽出
    sender_continent = determine_sender_continent(data['sender_municipality'])
    receiver_continent = determine_receiver_continent(
        data['receiver_municipality']
    )

    # トランザクションデータをJSON文字列に変換
    transaction_data_json = json.dumps(data, sort_keys=True).encode('utf-8')

    # トランザクションデータの検証
    try:
        validate_transaction_data(data)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    # NTRU暗号用鍵ペア生成
    try:
        ntru_public_key, ntru_private_key = generate_ntru_keys()
    except Exception as e:
        return jsonify(
            {"error": f"Failed to generate NTRU keys: {str(e)}"}
        ), 500

    # トランザクションデータをNTRU公開鍵で暗号化
    try:
        encrypted_data = encrypt_transaction_data(
            transaction_data_json.decode('utf-8'), ntru_instance
        )
    except Exception as e:
        return jsonify(
            {"error": f"Failed to encrypt transaction data: {str(e)}"}
        ), 500
    
    # ここで NTRU暗号化
    message_poly = [ord(ch) for ch in data['message_str']]
    rand_poly = [1, 0, -1, 1]  # 適当な乱数多項式
    ciphertext = ntru_instance.encrypt(message_poly, rand_poly)
    
    # ciphertextを data['encrypted_data'] に格納して送る
    data['encrypted_data'] = ciphertext
    
    # pqcrypto署名用鍵ペア生成
    try:
        pq_public_key, pq_private_key = generate_pq_keys()
    except Exception as e:
        return jsonify(
            {"error": f"Failed to generate Dilithium keys: {str(e)}"}
        ), 500

    # トランザクションデータにpqcrypto用の秘密鍵で署名を生成
    try:
        signature = generate_signature(transaction_data_json, pq_private_key)
    except Exception as e:
        return jsonify(
            {"error": f"Failed to generate signature: {str(e)}"}
        ), 500

    # トランザクションデータを整形
    transaction = {
        "sender": data['sender'],
        "receiver": data['receiver'],
        "to_wallet": data['to_wallet'],
        "from_wallet": data['from_wallet'],
        "amount": float(data['amount']),
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "transaction_id": str(uuid.uuid4()),
        "encrypted_data": encrypted_data,
        "signature": signature,  # 署名を追加
        "ntru_public_key": base64.b64encode(ntru_public_key).decode('utf-8'),
        "pq_public_key": base64.b64encode(pq_public_key).decode('utf-8'),
        "sender_municipality": data['sender_municipality'],
        "receiver_municipality": data['receiver_municipality'],
        "sender_continent": sender_continent,
        "receiver_continent": receiver_continent,
        "status": "send_pending",
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        "attributes":Attributes,
    }

    # 送信トランザクションの代表者を選出（DPoS）
    dpos = DPoS(sender_municipalities, receiver_municipalities)
    sender_rep = dpos.elect_representative('sender')
    receiver_rep = dpos.elect_representative('receiver')

    # トランザクションの承認
    if dpos.approve_transaction(transaction):
        try:
            mongo_uri = get_mongo_uri(
                "send_pending", transaction['sender_continent']
            )
            mongo_client = MongoClient(mongo_uri)
            mongo_collection = mongo_client['transactions_db']['transactions']
            mongo_collection.insert_one(transaction)
            print(
                "Transaction inserted successfully with status 'send_pending'"
            )
        except Exception as e:
            print(f"Failed to insert transaction: {e}")
            return jsonify({"error": "Failed to insert transaction"}), 500

        municipal_chain_url = determine_municipal_chain(
            transaction['sender_municipality'],
            transaction['receiver_municipality']
        )
        print(f"Sending to Municipal Chain URL: {municipal_chain_url}")

        try:
            response = requests.post(
                f'{municipal_chain_url}/receive_transaction', json=transaction
            )
            if response.status_code == 200:
                print("Transaction sent successfully to Municipal Chain")
                return jsonify({"status": "success"}), 200
            else:
                print(f"Failed to send transaction: {response.text}")
                return jsonify(
                    {"error": "Failed to send transaction"}
                ), response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Error occurred: {str(e)}")
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Failed to approve transaction"}), 500


# トランザクション生成と未完了トランザクション管理のための関数
def send_to_municipal_chain(transaction, municipal_chain_url):
    try:
        response = requests.post(
            f'{municipal_chain_url}/receive_transaction', json=transaction
        )
        if response.status_code == 200:
            print("Transaction sent successfully to Municipal Chain")
            # Municipal Chainに送信が成功したら、Continental Main Chainに未完了トランザクションを送信
            send_to_continental_main_chain(transaction)
            return response.json()
        else:
            print(f"Failed to send transaction: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {str(e)}")
        return None


def send_to_continental_main_chain(transaction):
    continental_chain_url = determine_continental_chain_url(
        transaction['continent'], transaction['municipality']
    )

    try:
        response = requests.post(
            f'{continental_chain_url}/pending_transaction', json=transaction
        )
        if response.status_code == 200:
            print("Transaction successfully sent to Continental Main Chain")
            return response.json()
        else:
            print(f"Failed to send to Continental Main Chain: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(
            f"Error occurred when sending to Continental Main Chain: {str(e)}"
        )
        return None


def create_indexes(instance_type, continent):
    mongo_uri = get_mongo_uri(instance_type, continent)
    mongo_client = MongoClient(mongo_uri)
    mongo_collection = mongo_client['transactions_db']['transactions']

    existing_indexes = mongo_collection.index_information()
    required_indexes = [("status", 1), ("created_at", 1)]

    for index in required_indexes:
        if index not in existing_indexes.values():
            mongo_collection.create_index([index])
    print(
        f"Indexes ensured on 'status'"
        f"'created_at' for {instance_type} in {continent}."
    )


@app.route("/send", methods=["POST"])
def send():
    wallet_address = request.form['wallet_address']
    recipient = request.form['recipient']
    amount = int(request.form['amount'])
    
    # トランザクションをimmuDBに保存する処理
    # （この部分は適切にトランザクションデータを immuDB に追加するコードが必要です）
    
    # 残高計算の更新
    balance = get_wallet_balance(wallet_address)
    return render_template('index.html', wallet_address=wallet_address, balance=balance)


def record_transaction(from_wallet, to_wallet, amount):
    client = ImmudbClient()
    client.login("immudb", "password")
    
    # トランザクションデータ
    tx_data = {
        "from_wallet": from_wallet,
        "to_wallet": to_wallet,
        "amount": amount,
        "timestamp": "2024-12-08T12:00:00Z",  # 仮のタイムスタンプ
        "status": "completed"
    }
    
    # immuDBにトランザクションを保存
    tx_id = f"tx:{from_wallet}:{to_wallet}:{amount}"
    client.set(tx_id.encode('utf-8'), str(tx_data).encode('utf-8'))


# 呼び出し時
create_indexes("send_pending", "Asia")


def clean_expired_send_pending_transactions(continent):
    while True:
        try:
            mongo_uri = get_mongo_uri("send_pending", continent)
            mongo_client = MongoClient(mongo_uri)
            mongo_collection = mongo_client['transactions_db']['transactions']
            expiration_threshold = (
                datetime.now(timezone.utc) - timedelta(days=6 * 30)
            )

            result = mongo_collection.delete_many({
                "status": "send_pending",
                "created_at": {"$lt": expiration_threshold.isoformat() + "Z"},
                "sender_municipal_id": {"$exists": True}
            })

            print(
                f"Deleted {result.deleted_count} expired "
                f"send_pending transactions for {continent}."
            )

        except Exception as e:
            print(f"Error during cleanup for {continent}: {e}")

        time.sleep(24 * 60 * 60)  # 24時間


# アプリケーション開始時にクリーンアップタスクを開始
cleanup_thread = threading.Thread(
    target=clean_expired_send_pending_transactions, args=("Asia",), daemon=True
)
cleanup_thread.start()

# 分析用MongoDBのURIを取得
try:
    # 環境変数またはデフォルト値を使用
    current_continent = os.getenv('CURRENT_CONTINENT', 'Asia')
    ANALYTICS_MONGO_URI = get_mongo_uri("analytics", current_continent)
    analytics_client = MongoClient(ANALYTICS_MONGO_URI)
    analytics_collection = analytics_client['analytics_db']['transactions']
    print(
        f"Successfully connected to analytics MongoDB instance "
        f"for {current_continent}"
    )
except Exception as e:
    print(f"Error connecting to analytics MongoDB: {e}")


def migrate_to_analytics(transaction, continent):
    try:
        mongo_uri = get_mongo_uri("analytics", continent)
        analytics_client = MongoClient(mongo_uri)
        analytics_collection = analytics_client['analytics_db']['transactions']

        # 分析用データベースにトランザクションをコピー
        analytics_collection.insert_one(transaction)
        print(
            f"Transaction {transaction['transaction_id']} "
            f"migrated to analytics database."
        )
    except Exception as e:
        print(
            f"Failed to migrate transaction {transaction['transaction_id']}: "
            f"{e}"
        )


@app.route("/login", methods=["POST"])
def login():
    wallet_address = request.form['wallet_address']
    password = request.form['password']  # パスワード認証はここでは省略します
    balance = get_wallet_balance(wallet_address)
    return render_template('index.html', wallet_address=wallet_address, balance=balance)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
    # ここで動的に大陸名を取得する
    current_continent = os.getenv('CURRENT_CONTINENT', 'Default')
    flask_port = get_flask_port(current_continent)

    # インデックスを作成
    create_indexes("send_pending", current_continent)

    # クリーンアップタスクを開始
    cleanup_thread = threading.Thread(
        target=clean_expired_send_pending_transactions,
        args=(current_continent,),
        daemon=True
    )
    cleanup_thread.start()

    app.run(host='0.0.0.0', port=flask_port)


@app.route('/example')
def example_redirect():
    return redirect(url_for('home'))


# PoH (Proof of History) の導入
import threading
import hashlib
from collections import deque


class ProofOfHistory:
    """
    簡易版のPoH実装例:
      - sequence: PoHイベントの履歴（例: 各トランザクションIDやそのハッシュを連結）
      - current_hash: 最新のPoHハッシュ
    """
    def __init__(self):
        self.sequence = deque()
        self.current_hash = None

    def add_event(self, event_data: str, event_timestamp: str):
        """
        新しいイベントを PoH 連鎖に追加する。
          event_data: 追加するデータ(例: トランザクションID 等)
          event_timestamp: イベントのタイムスタンプ
        """
        # 1. イベント文字列を生成
        #    例: "event_data:xxxx / timestamp:yyyy" のように連結
        event_str = f"{event_data}:{event_timestamp}"
        
        # 2. 既存の current_hash と event_str を連結して新しいハッシュを作る
        base_input = (self.current_hash if self.current_hash else "").encode('utf-8')
        event_input = event_str.encode('utf-8')
        
        hasher = hashlib.sha256()
        hasher.update(base_input)
        hasher.update(event_input)
        new_hash = hasher.hexdigest()
        
        # 3. sequence にイベントを追加し、current_hash を更新
        self.sequence.append(event_str)
        self.current_hash = new_hash

    def get_latest_hash(self) -> str:
        """ 現在のPoHのハッシュを取得 """
        return self.current_hash if self.current_hash else ""

    def get_sequence_list(self) -> list:
        """ これまでに追加したPoHイベントを一覧で返す（デバッグ用） """
        return list(self.sequence)

    def __len__(self):
        """ イベント数を返す """
        return len(self.sequence)


# グローバル PoH インスタンス
poh = ProofOfHistory()