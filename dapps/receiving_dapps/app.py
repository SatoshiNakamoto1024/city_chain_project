from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import json
from pymongo import MongoClient
from datetime import datetime, timezone
from bson import json_util
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from ntru_encryption import Ntru
from ntru_lib import generate_ntru_keys, decrypt_message, verify_signature
# immuDB 関連の import など
import grpc
from immudb_proto import immu_service_client, schema_pb2 as schema
from immudb_proto.immu_service_client import ImmuServiceClient
# 既存の import に加えて
import hashlib
import time
import threading
from collections import deque

# PoH (Proof of History) のクラス
class ProofOfHistory:
    """
    簡易的なPoH実装:
      - sequence: イベント(=トランザクションIDやそのタイムスタンプ)を保持
      - current_hash: 今までのPoH連鎖の最新ハッシュ
    """
    def __init__(self):
        self.sequence = deque()
        self.current_hash = None

    def add_event(self, event_str: str):
        """
        PoHに新たなイベント（文字列）を追加し、ハッシュ連鎖を更新する。
        event_str: "tx_id:timestamp" などの連結文字列を想定
        """
        # 1. 現在のcurrent_hashをバイト列化（無い場合は空）
        base = (self.current_hash if self.current_hash else "").encode('utf-8')
        
        # 2. 新イベントの文字列をバイト列化し、結合してハッシュ
        new_input = event_str.encode('utf-8')
        hasher = hashlib.sha256()
        hasher.update(base)
        hasher.update(new_input)
        new_hash = hasher.hexdigest()
        
        # 3. sequenceにイベントを追加し、current_hash更新
        self.sequence.append(event_str)
        self.current_hash = new_hash

    def get_latest_hash(self) -> str:
        """PoHチェーンの最新ハッシュを返す"""
        return self.current_hash if self.current_hash else ""

    def get_sequence_list(self) -> list:
        """PoHに追加されたイベント一覧を返す（デバッグ用）"""
        return list(self.sequence)

    def __len__(self):
        return len(self.sequence)


# グローバル PoH インスタンスを生成
poh = ProofOfHistory()

# BASE_DIRを先に定義
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# グローバル or app.config などに NTRU インスタンスを保持
# （鍵ペア生成は後述）
ntru_instance = None

# サーバー起動時に鍵を生成
ntru_keys = generate_ntru_keys()

KEY_FILE_PATH = os.path.join(BASE_DIR, 'ntru_keys.json')


@app.route("/init_ntru", methods=["POST"])
def init_ntru():
    global ntru_instance
    data = request.json
    N = data["N"]
    p = data["p"]
    q = data["q"]

    # Ntru インスタンスを作成
    ntru_instance = Ntru(N, p, q)
    return "NTRU initialized", 200


@app.route("/generate_ntru_keys", methods=["POST"])
def generate_ntru_keys():
    global ntru_instance
    if not ntru_instance:
        return "NTRU is not initialized. Call /init_ntru first.", 400
    
    # 例: f, g, d はクライアントから受け取るか、サンプルで固定する
    data = request.json
    f_new = data["f"]
    g_new = data["g"]
    d_new = data["d"]  # e.g. 7 など
    
    try:
        ntru_instance.genPublicKey(f_new, g_new, d_new)
    except Exception as e:
        return f"Error generating public key: {e}", 400
    
    # 公開鍵 h を返す or 保存する
    public_key = ntru_instance.getPublicKey()
    return {"public_key": public_key}, 200


def load_ntru_keys():
    if os.path.exists(KEY_FILE_PATH):
        with open(KEY_FILE_PATH, 'r') as f:
            keys_data = json.load(f)
            return NTRUKeys(
                public_key=bytes.fromhex(keys_data['public_key']),
                private_key=bytes.fromhex(keys_data['private_key'])
            )
    else:
        keys = generate_ntru_keys()
        with open(KEY_FILE_PATH, 'w') as f:
            json.dump({
                'public_key': keys.public_key.hex(),
                'private_key': keys.private_key.hex()
            }, f)
        return keys

ntru_keys = load_ntru_keys()

app = Flask(__name__, static_folder='static')
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'  # 秘密のキーを設定
app.secret_key = 'your_secret_key'  # Flaskのセッション管理用
jwt = JWTManager(app)
CORS(app)  # クロスオリジンリソースシェアリングを許可
JWT_SECRET = 'jwt_secret_key'  # JWTのシークレット

# MongoDB設定ファイルパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MONGODB_CONFIG_PATH = os.path.join(BASE_DIR, 'mongodb_config.json')

# MongoDB設定ファイルを読み込む
def load_mongodb_config():
    try:
        with open(MONGODB_CONFIG_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: '{MONGODB_CONFIG_PATH}' not found. Please check the path.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from '{MONGODB_CONFIG_PATH}': {e}")

mongodb_config = load_mongodb_config()

# MongoDB URI を取得する関数
def get_mongo_uri(instance_type, continent):
    if instance_type in mongodb_config and continent in mongodb_config[instance_type]:
        return mongodb_config[instance_type][continent]
    elif instance_type in mongodb_config and 'Default' in mongodb_config[instance_type]:
        return mongodb_config[instance_type]['Default']
    else:
        raise ValueError(f"MongoDB URI not found for instance type '{instance_type}' and continent '{continent}'")

def get_mongo_connection(instance_type, continent):
    mongo_uri = get_mongo_uri(instance_type, continent)
    client = MongoClient(mongo_uri)
    return client

# グローバル変数 municipalities_data の初期化
municipalities_data = {}

# municipalities.json の読み込み
municipalities_file_path = os.path.join(BASE_DIR, 'municipalities.json')

# ファイルが存在するか確認
if not os.path.exists(municipalities_file_path):
    raise FileNotFoundError(f"Error: '{municipalities_file_path}' not found. Please check the path.")

# ファイルを開くときにエラーハンドリングを追加
try:
    with open(municipalities_file_path, 'r', encoding='utf-8') as file:
        municipalities_data = json.load(file)
except json.JSONDecodeError as e:
    raise ValueError(f"Error decoding JSON from '{municipalities_file_path}': {e}")
except Exception as e:
    raise RuntimeError(f"An error occurred while reading '{municipalities_file_path}': {e}")

def determine_receiver_continent(receiver_municipality):
    try:
        # 'continent-city' の形式から大陸名を抽出
        continent = receiver_municipality.split('-')[0]
        return continent
    except IndexError:
        return "Default"

def determine_municipal_chain(sender_municipality, receiver_municipality):
    global municipalities_data  # グローバル変数を参照する

    # 市町村の URL を保存するための辞書を初期化
    municipal_chain_urls = {}

    # 大陸ごとの市町村情報をループしてURLを設定
    for continent, continent_data in municipalities_data.items():
        for city_data in continent_data.get('cities', []):
            # cities データから各市町村のURLを構築
            city_name = city_data['name']
            city_port = city_data['city_flask_port']  # 修正: 'city_port' から 'city_flask_port'へ
            municipal_chain_urls[f"{continent}-{city_name}"] = f"http://127.0.0.1:{city_port}"

    # 送信者または受信者の市町村に基づいて Municipal Chain の URL を選択
    if sender_municipality in municipal_chain_urls:
        return municipal_chain_urls[sender_municipality]
    elif receiver_municipality in municipal_chain_urls:
        return municipal_chain_urls[receiver_municipality]
    else:
        # デフォルトの city_flask_port を使用する
        default_city_port = municipalities_data['Default']['cities'][0]['city_flask_port']
        return f"http://127.0.0.1:{default_city_port}"  # その他の市町村チェーン（デフォルト）


# ★immuDB を用いたウォレット管理のためのヘルパー関数を追加
IMMUDB_WALLET_PREFIX = "wallet_"  # immuDBでウォレットを管理するキーのプレフィックス


def connect_to_immudb():
    """
    immuDBに接続するためのヘルパー。
    実際には接続情報やユーザー情報は環境変数や設定ファイルで安全に管理することを推奨。
    """
    channel = grpc.insecure_channel("localhost:3322")  # immuDBがlocalhost:3322で立ち上がっている例
    client = ImmuServiceClient(channel)
    # ログイン
    login_req = schema.LoginRequest(user="immudb", password="immudb")
    client.service.Login(login_req)
    return client


def save_wallet_to_immudb(user_id: str, balance: float):
    """
    user_id のウォレット残高を immuDB に保存(上書き)する。
    """
    client = connect_to_immudb()
    wallet_key = (IMMUDB_WALLET_PREFIX + user_id).encode("utf-8")
    wallet_value = str(balance).encode("utf-8")

    set_request = schema.SetRequest(kvs=[schema.KeyValue(key=wallet_key, value=wallet_value)])
    client.service.Set(set_request)
    print(f"[immuDB] user_id={user_id} balance={balance} saved.")


def get_wallet_from_immudb(user_id: str) -> float:
    """
    user_id のウォレット残高を immuDB から取得する (無ければ0として扱う)。
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
        # keyが存在しない場合など
        return 0.0


def update_wallet_in_immudb(user_id: str, delta: float) -> float:
    """
    user_id のウォレット残高を immuDB上で delta 分加減算し、更新後の残高を返す。
    """
    current_balance = get_wallet_from_immudb(user_id)
    new_balance = current_balance + delta
    if new_balance < 0:
        new_balance = 0
    save_wallet_to_immudb(user_id, new_balance)
    return new_balance


# MongoDB側のwallet_collectionが必要なら、以下を使う
mongo_client = MongoClient("mongodb://localhost:27017")
wallet_collection = mongo_client["wallet_db"]["wallets"]


def get_wallet_balance_both(user_id: str) -> float:
    """
    MongoDBとimmuDBの両方を参照し、例えば「大きい方を返す」などのポリシーで最終的な残高を返す。
    """
    # MongoDB 側
    doc = wallet_collection.find_one({"user_id": user_id})
    mongo_balance = 0.0
    if doc and "balance" in doc:
        mongo_balance = float(doc["balance"])

    # immuDB 側
    immu_balance = get_wallet_from_immudb(user_id)

    # 例: 大きい方を返す
    return max(mongo_balance, immu_balance)


def update_wallet_balance_both(user_id: str, amount: float):
    """
    MongoDBとimmuDBの両方を更新する。
    """
    # 1) MongoDB 側を更新
    user_doc = wallet_collection.find_one({"user_id": user_id})
    if not user_doc:
        new_mongo_balance = amount
        wallet_collection.insert_one(
            {"user_id": user_id, "balance": new_mongo_balance}
        )
    else:
        new_mongo_balance = user_doc["balance"] + amount
        if new_mongo_balance < 0:
            new_mongo_balance = 0
        wallet_collection.update_one(
            {"user_id": user_id},
            {"$set": {"balance": new_mongo_balance}}
        )

    # 2) immuDB 側を更新
    new_immu_balance = update_wallet_in_immudb(user_id, amount)

    print(f"[Both] user_id={user_id}, new_mongo_balance={new_mongo_balance}, new_immu_balance={new_immu_balance}")


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # ユーザー認証の簡単な例
    if username in users and users[username] == password:
        # JWTを発行
        token = jwt.encode({
            'username': username,
            # 1時間有効
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, JWT_SECRET, algorithm='HS256')

        return jsonify({'token': token})
    else:
        return jsonify({'message': 'Invalid credentials'}), 401


@app.route("/ntru_encrypt", methods=["POST"])
def ntru_encrypt():
    global ntru_instance
    if not ntru_instance:
        return "NTRU not initialized", 400
    
    data = request.json
    message_poly = data["message"]  # list of int
    rand_poly = data["rand"]       # list of int
    
    try:
        cipher = ntru_instance.encrypt(message_poly, rand_poly)
    except Exception as e:
        return f"Encrypt error: {e}", 400
    
    return {"encrypted": cipher}, 200


@app.route("/ntru_decrypt", methods=["POST"])
def ntru_decrypt():
    global ntru_instance
    if not ntru_instance:
        return "NTRU not initialized", 400
    
    data = request.json
    enc_poly = data["encrypted"]  # list[int]
    
    try:
        plaintext_poly = ntru_instance.decrypt(enc_poly)
    except Exception as e:
        return f"Decrypt error: {e}", 400
    
    return {"plaintext": plaintext_poly}, 200


@app.route("/receive_secure_data", methods=["POST"])
def receive_secure_data():
    global ntru_instance
    if not ntru_instance:
        return "NTRU not ready", 400
    
    data = request.json
    encrypted_poly = data["encrypted_poly"]  # list[int], from the sender
    try:
        # 復号
        decrypted_poly = ntru_instance.decrypt(encrypted_poly)
    except Exception as e:
        return f"Decrypt error: {e}", 400
    
    # decrypted_poly から元のメッセージを再構築（実際には多項式→文字列など）
    # ...
    return {"status": "ok", "decrypted": decrypted_poly}


@app.route('/')
def serve_index():
    if app.static_folder is not None:
        return send_from_directory(app.static_folder, 'index.html')
    else:
        return "Static folder is not set", 404

@app.route('/api/municipalities', methods=['GET'])
def get_municipalities():
    try:
        municipalities = []
        for continent, data in municipalities_data.items():
            for city in data.get('cities', []):
                city_id = f"{continent}-{city['name']}"
                municipalities.append({
                    "id": city_id,
                    "name": city['name'],
                    "continent": continent
                })
        return jsonify(municipalities), 200
    except Exception as e:
        print(f"Error fetching municipalities: {e}")
        return jsonify({'message': 'Internal server error.'}), 500


@app.route('/api/receivers', methods=['GET'])
def get_receivers():
    try:
        # すべての大陸を対象にする
        receivers_set = set()
        for continent in municipalities_data.keys():
            # MongoDBに接続
            mongo_client = get_mongo_connection("send_pending", continent)
            mongo_collection = mongo_client['transactions_db']['transactions']

            # `status` が 'send_pending' のトランザクションから受信者を取得
            transactions_cursor = mongo_collection.find({'status': 'send_pending'})
            for txn in transactions_cursor:
                receivers_set.add(txn['receiver'])

        # 受信者名のリストを作成
        receivers = [{'name': receiver} for receiver in receivers_set]
        return jsonify(receivers), 200
    except Exception as e:
        print(f"Error fetching receivers: {e}")
        return jsonify({'message': 'Internal server error.'}), 500


@app.route('/api/pending_transactions', methods=['GET'])
@jwt_required()
def get_pending_transactions():
    try:
        # クエリパラメータから受信者の識別子を取得
        receiver = request.args.get('receiver')
        receiver_municipality = request.args.get('receiver_municipality')
        if not receiver or not receiver_municipality:
            return jsonify({'message': 'Receiver identifier and receiver municipality are required.'}), 400

        # 大陸情報を抽出
        receiver_continent = determine_receiver_continent(receiver_municipality)

        # MongoDBに接続
        mongo_client = get_mongo_connection("send_pending", receiver_continent)
        mongo_collection = mongo_client['transactions_db']['transactions']

        # クエリを実行
        transactions_cursor = mongo_collection.find({
            'receiver': receiver,
            'receiver_municipal_id': receiver_municipality,
            'status': 'send_pending'
        })

        transactions = []
        for txn in transactions_cursor:
            txn['_id'] = str(txn['_id'])
            # datetimeオブジェクトを文字列に変換
            if 'created_at' in txn and isinstance(txn['created_at'], datetime):
                txn['created_at'] = txn['created_at'].isoformat()
            if 'updated_at' in txn and isinstance(txn['updated_at'], datetime):
                txn['updated_at'] = txn['updated_at'].isoformat()
            transactions.append(txn)

        return jsonify(transactions), 200

    except Exception as e:
        print(f"Error fetching pending transactions: {e}")
        return jsonify({'message': 'Internal server error.'}), 500

@app.route('/api/receive_transaction', methods=['POST'])
@jwt_required()
def receive_transaction():
    data = request.get_json()
    transaction_id = data.get('transaction_id')
    receiver_municipality = data.get('receiver_municipality')

    if not transaction_id or not receiver_municipality:
        return jsonify({'message': 'transaction_id and receiver_municipality are required.'}), 400

    try:
        # 大陸情報を抽出
        receiver_continent = determine_receiver_continent(receiver_municipality)

        # MongoDBに接続
        mongo_client = get_mongo_connection("send_pending", receiver_continent)
        mongo_collection = mongo_client['transactions_db']['transactions']

        # トランザクションを取得
        transaction = mongo_collection.find_one({
            'transaction_id': transaction_id,
            'receiver_municipal_id': receiver_municipality
        })

        if not transaction:
            return jsonify({'message': 'Transaction not found.'}), 404
        
        # 受信を完了したら、PoHにイベントを追加
        # イベント文字列: "transaction_id:現在時刻" などを作成
        global poh
        now_str = datetime.now(timezone.utc).isoformat()
        event_str = f"{transaction_id}:{now_str}"
        poh.add_event(event_str)
        print(f"[PoH] Added event='{event_str}' => latest_hash={poh.get_latest_hash()}")

        # 暗号化データと署名を取得
        encrypted_data = transaction.get('encrypted_data')
        signature = transaction.get('signature')

        if not encrypted_data or not signature:
            return jsonify({'message': 'Missing encrypted data or signature.'}), 400

        # データの復号化
        decrypted_data = decrypt_transaction_data(encrypted_data)
        decrypted_transaction = json.loads(decrypted_data)

        # 署名の検証
        decrypted_data_str = json.dumps(decrypted_transaction, sort_keys=True)
        is_valid_signature = verify_transaction_signature(decrypted_data_str, signature, ntru_keys.public_key)

        if not is_valid_signature:
            return jsonify({'message': 'Invalid signature.'}), 400

        # ウォレットに残高を加算するなどの処理:
        # たとえば receiver が受け取った amount だけ残高を増やす
        amount = decrypted_transaction.get("amount", 0)
        receiver = decrypted_transaction.get("receiver")  # user_id
        if receiver and amount:
            # receiving userに amount加算
            update_wallet_balance_both(receiver, amount)

        # トランザクションのステータスを 'receive_pending' に更新
        result = mongo_collection.update_one(
            {'transaction_id': transaction_id, 'receiver_municipal_id': receiver_municipality},
            {'$set': {'status': 'receive', 'updated_at': datetime.now(timezone.utc)}}
        )

        if result.modified_count == 0:
            return jsonify({'message': 'Failed to update transaction status.'}), 500

        # BSONドキュメントをJSONに変換
        transaction_json = json.loads(json_util.dumps(transaction))

        # '_id' フィールドを削除
        transaction_json.pop('_id', None)

        # Municipal Chain の URL を決定
        municipal_chain_url = determine_municipal_chain(transaction_json['sender_municipality'], transaction_json['receiver_municipality'])

        # トランザクションを Municipal Chain に送信
        response = requests.post(f'{municipal_chain_url}/receive_transaction', json=transaction_json)

        if response.status_code in [200, 202]:
            # トランザクションのステータスを 'complete' に更新
            result = mongo_collection.update_one(
                {'transaction_id': transaction_id, 'receiver_municipal_id': receiver_municipality},
                {'$set': {'status': 'complete', 'updated_at': datetime.now(timezone.utc)}}
            )
            if result.modified_count == 0:
                return jsonify({'message': 'Failed to update transaction status to complete.'}), 500

            print(f"Transaction {transaction_id} status updated to 'complete'.")

            # ステータスが 'complete' になったので、トランザクションを分析用データベースに移行
            try:
                analytics_uri = get_mongo_uri("analytics", receiver_continent)
                analytics_client = MongoClient(analytics_uri)
                analytics_collection = analytics_client['analytics_db']['transactions']

                # トランザクションを挿入
                analytics_collection.insert_one(transaction)
                print(
                    f"Transaction {transaction_id} migrated to analytics database."
                )

                # オペレーショナルデータベースからトランザクションを削除
                mongo_collection.delete_one(
                    {'transaction_id': transaction_id, 'receiver_municipal_id': receiver_municipality}
                )
            except Exception as e:
                print(f"Failed to migrate transaction: {e}")
                return jsonify({'message': 'Failed to migrate transaction to analytics database.'}), 500

            return jsonify({'message': f'Transaction {transaction_id} received and processed successfully.'}), 200
        else:
            try:
                error_msg = response.json().get('message', 'Failed to process transaction.')
            except json.JSONDecodeError:
                error_msg = 'Failed to process transaction.'
            return jsonify({'message': error_msg}), response.status_code
    except Exception as e:
        print(f"Error receiving transaction: {e}")
        return jsonify({'message': 'Internal server error.'}), 500


@app.route('/api/poh_status', methods=['GET'])
def get_poh_status():
    """
    PoHの状態をJSONで返す。
    """
    global poh
    return jsonify({
        "latest_hash": poh.get_latest_hash(),
        "event_count": len(poh),
        "sequence": poh.get_sequence_list()  # デバッグ用に全イベント一覧を返す
    }), 200


def poh_continuous_update():
    """一定間隔でPoHにダミーイベントを追加し続けるスレッド用関数。"""
    global poh
    while True:
        time.sleep(1.0)  # 1秒おき
        now_str = datetime.now(timezone.utc).isoformat()
        dummy_event = f"tick:{now_str}"
        poh.add_event(dummy_event)
        print(f"[PoH Thread] event='{dummy_event}', latest_hash={poh.get_latest_hash()}")


# アプリ起動時にスレッドを開始
poh_thread = threading.Thread(target=poh_continuous_update, daemon=True)
poh_thread.start()


def decrypt_transaction_data(encrypted_data):
    global ntru_keys
    ciphertext = bytes.fromhex(encrypted_data['ciphertext'])
    encrypted_message = bytes.fromhex(encrypted_data['encrypted_message'])
    decrypted_data = decrypt_message(ciphertext, encrypted_message, ntru_keys.private_key)
    return decrypted_data.decode('utf-8')


def verify_transaction_signature(data, signature, public_key):
    signature_bytes = bytes.fromhex(signature)
    return verify_signature(data.encode('utf-8'), signature_bytes, public_key)


# トランザクションの拒否機能（オプション）
@app.route('/api/reject_transaction', methods=['POST'])
def reject_transaction():
    data = request.get_json()
    transaction_id = data.get('transaction_id')
    receiver_municipality = data.get('receiver_municipality')

    if not transaction_id or not receiver_municipality:
        return jsonify({'message': 'transaction_id and receiver_municipality are required.'}), 400

    try:
        receiver_continent = determine_receiver_continent(receiver_municipality)
        mongo_client = get_mongo_connection("send_pending", receiver_continent)
        mongo_collection = mongo_client['transactions_db']['transactions']

        result = mongo_collection.update_one(
            {'transaction_id': transaction_id, 'receiver_municipal_id': receiver_municipality},
            {'$set': {'status': 'rejected', 'updated_at': datetime.now(timezone.utc)}}
        )

        if result.modified_count == 0:
            return jsonify({'message': 'Failed to update transaction status.'}), 500

        return jsonify({'message': f'Transaction {transaction_id} rejected successfully.'}), 200
    except Exception as e:
        print(f"Error rejecting transaction: {e}")
        return jsonify({'message': 'Internal server error.'}), 500


if __name__ == '__main__':
    # 環境変数またはデフォルト値から大陸名を取得
    current_continent = os.getenv('CURRENT_CONTINENT', 'Default')

    # Flask ポートを取得
    flask_port = municipalities_data.get(current_continent, {}).get('flask_port', 5000)
    try:
        flask_port = int(flask_port)
    except ValueError:
        print(
            f"Invalid port number '{flask_port}' for continent '{current_continent}'."
            f"Using default port 5000."
        )
        flask_port = 5000

    # アプリケーションを起動
    app.run(host='0.0.0.0', port=flask_port, debug=True)
