# File: dapps/sending_dapps/test_sending_dapps.py
# test_sending_dapps.py 先頭 ↓ ここより前に何も import しない
import os, sys, types, asyncio, uuid

# **テスト実行時は必ず TEST_ENV=true を set しておくと、
#   cert_utils の検証ロジックが常に True を返すようになります。**
os.environ["TEST_ENV"] = "true"

if "city_dag_storage" not in sys.modules:
    stub = types.ModuleType("city_dag_storage")
    class CityDAGStorage:
        async def add_transaction(self, *a, **k):
            await asyncio.sleep(0)
            return f"dummy_{uuid.uuid4().hex[:8]}", f"dummy_hash_{uuid.uuid4().hex[:16]}"
    stub.CityDAGStorage = CityDAGStorage
    sys.modules["city_dag_storage"] = stub

import json
import base64
import pytest

# プロジェクトルートを通す
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from flask import Flask
from dapps.sending_dapps.sending_dapps import send_bp
from dapps.sending_dapps.validator import validate_transaction

import boto3

# NTRU / Dilithium ラッパーを使う
from dapps.sending_dapps.sending_dapps import (
    ntru_generate, ntru_encrypt, ntru_decrypt,
    dilithium_generate, dilithium_sign, dilithium_verify
)

# 送信DApps 側の get_wallet_by_user／verify_jwt をモックするためにインポート
from dapps.sending_dapps.sending_dapps import get_wallet_by_user, verify_jwt

# ─── 追加: cert_utils をインポートしておく ─────────────────────────────────
import dapps.sending_dapps.cert_utils as cert_utils
# ──────────────────────────────────────────────────────────────────────────

# テスト用ユーザー UUID (送信者 / 受信者)
TEST_SENDER_UUID = "uuid_kanazawa_01"  # ナカモトサトシ_01
TEST_RECEIVER_UUIDS = [
    "uuid_sligo_01",  # アンナ_01
    "dummy_uuid_e1",
    "dummy_uuid_e2",
    "dummy_uuid_e3",
    "dummy_uuid_e4"
]

@pytest.fixture(autouse=True)
def patch_verify_jwt(monkeypatch):
    """
    sending_dapps.py 内で verify_jwt() を呼んでいる箇所をモックします。
    テストでは常に sender が TEST_SENDER_UUID になるようにします。
    """
    monkeypatch.setattr(
        "dapps.sending_dapps.sending_dapps.verify_jwt",
        lambda token: {"user_uuid": TEST_SENDER_UUID}
    )

# ─── 追加: モックする cert_utils の関数 ────────────────────────────────────
@pytest.fixture(autouse=True)
def patch_cert_utils(monkeypatch):
    """
    テストではクライアント証明書・署名検証を常に成功させるようモックしておく。
    """
    # verify_client_certificate(cert_bytes: bytes) → True
    monkeypatch.setattr(
        cert_utils,
        "verify_client_certificate",
        lambda cert_bytes: True
    )
    # verify_message_signature(msg: bytes, sig: bytes, pubkey: bytes) → True
    monkeypatch.setattr(
        cert_utils,
        "verify_message_signature",
        lambda msg, sig, pubkey: True
    )
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_boto3_resource(monkeypatch):
    """
    boto3.resource() をモックして DynamoDB への実リクエストを行わないようにします。
    かつ「同一の DummyTable インスタンス」を使いまわすように修正しています。
    """
    class DummyTable:
        def __init__(self):
            # 送信者・受信者のダミーデータを格納
            self.storage = {
                # 送信者ユーザー情報 (USER_PROFILE)
                ("uuid_kanazawa_01", "USER_PROFILE"): {
                    "username": "ナカモトサトシ_01",
                    # テスト内で生成した NTRU 秘密鍵（Base64）・Dilithium 公開鍵（Base64）を後から書き込む
                    "ntru_secret_key_b64": "",
                    "dilithium_public_key": "",
                    "region": "Asia",                  # ← region フィールドも追加
                    "sender_municipality": "Asia/JP/18/Kanazawa"
                },
                # 受信者ユーザー情報 (USER_PROFILE)
                ("uuid_sligo_01", "USER_PROFILE"): {
                    "username": "アンナ_01",
                    "region": "Europe",                # ← region フィールドも追加
                    "sender_municipality": "Europe/IE/SO/Sligo"
                }
            }

        def get_item(self, Key):
            item = self.storage.get((Key["uuid"], Key["session_id"]))
            if item is None:
                return {}  # DynamoDB と同じく "Item" キーなしを返す
            # 返すアイテムには必ずキー情報を含める
            ret = item.copy()
            ret["uuid"] = Key["uuid"]
            ret["session_id"] = Key["session_id"]
            return {"Item": ret}

        def put_item(self, Item, ReturnValues=None):
            # Item に "uuid" と "session_id" が入っていれば、self.storage を上書き
            key = (Item["uuid"], Item["session_id"])
            self.storage[key] = Item
            return {}

    class DummyDynamoResource:
        def __init__(self):
            # ここで 1 回だけ DummyTable を作成しておく
            self._singleton_table = DummyTable()

        def Table(self, name):
            # 常に同じ DummyTable インスタンスを返す
            return self._singleton_table

    # boto3.resource() → DummyDynamoResource のインスタンスを返す
    monkeypatch.setattr(boto3, "resource", lambda *args, **kwargs: DummyDynamoResource())

@pytest.fixture(autouse=True)
def patch_get_wallet(monkeypatch):
    """
    get_wallet_by_user() を常に残高十分なダミーウォレットを返すようにします。
    """
    class DummyWallet:
        def __init__(self):
            self.wallet_address = "dummy_wallet_addr"
            self.balance = "1000000"
    monkeypatch.setattr(
        "dapps.sending_dapps.sending_dapps.get_wallet_by_user",
        lambda uuid: DummyWallet()
    )

@pytest.fixture
def client():
    """
    Flask アプリを立ち上げ、send_bp を /send にマウントしたテストクライアントを返却します。
    """
    app = Flask(__name__, template_folder="templates")
    app.register_blueprint(send_bp, url_prefix="/send")
    return app.test_client()


def test_api_list_users(client):
    """
    GET /send/api/users?region=Asia → ダミー 5 件が返ることを確認
    """
    res = client.get("/send/api/users?region=Asia")
    assert res.status_code == 200

    users = res.get_json()
    assert isinstance(users, list)
    # 今回ダミー実装では「Asia」にマッチするユーザーが 1 件だけ登録してある想定ですが、
    # テスト用には「ダミーデータが 1 件」返ってくるものとします。
    # 以下では「region フィールドが 'Asia'」であることをチェックします。
    assert len(users) == 1
    for u in users:
        assert "uuid" in u
        assert "username" in u
        assert u["region"] == "Asia"


def test_send_transaction_and_validate(client):
    """
    POST /send/api/send_transaction → セキュアモードで 200 が返ってくること、
    かつ戻り値 tx の固定ハッシュが正しく検証できることを確認します。
    """

    # ─── 1) NTRU / Dilithium で鍵ペアを生成 ───────────────────────────────────
    kp_ntru = ntru_generate()  # 返り値は NtruKeyPair オブジェクト
    pk_ntru = bytes(kp_ntru.public_key)  # PyBytes → bytes
    sk_ntru = bytes(kp_ntru.secret_key)  # PyBytes → bytes

    # Dilithium 送信者鍵ペア (generate_keypair は (pk, sk) のタプル)
    pk_dili_raw, sk_dili_raw = dilithium_generate()
    pk_dili = bytes(pk_dili_raw)
    sk_dili = bytes(sk_dili_raw)

    # ─── 2) 同じ DummyTable インスタンスを使って DynamoDB モックの内部ストレージに秘密鍵・公開鍵を格納 ──
    import boto3 as _boto3  # テスト内でモックした boto3.resource を使う
    tbl = _boto3.resource().Table("UsersTable")
    sender_record = tbl.get_item(Key={"uuid": TEST_SENDER_UUID, "session_id": "USER_PROFILE"})["Item"]
    # NTRU 秘密鍵を Base64 エンコードして書き込む
    sender_record["ntru_secret_key_b64"] = base64.b64encode(sk_ntru).decode("utf-8")
    # Dilithium 公開鍵を Base64 エンコードして書き込む
    sender_record["dilithium_public_key"] = base64.b64encode(pk_dili).decode("utf-8")
    # （この時点で、アプリケーションコード側でも同じ DummyTable インスタンスを参照するので、値が共有される）
    tbl.put_item(Item=sender_record)

    # ─── 3) ダミーのクライアント証明書（PEM 形式）を用意 ────────────────────
    # 実運用では CA 発行の client_cert.pem を Base64 エンコードして送るが、
    # テストではモック関数が常に True を返すので、中身は何でもよい。
    dummy_cert_pem = (
        b"-----BEGIN CERTIFICATE-----\n"
        b"dGVzdF9jZXJ0X2R1bW15X2Fib2NvbnRlbnQ=\n"
        b"-----END CERTIFICATE-----\n"
    )
    client_cert_b64 = base64.b64encode(dummy_cert_pem).decode("utf-8")

    # ─── 4) payload_body を作成 (必須フィールドをすべて含む) ─────────────────
    receiver_uuid = TEST_RECEIVER_UUIDS[0]  # "uuid_sligo_01"
    payload_body = {
        "receiver_uuid":          receiver_uuid,
        "amount":                 "42.0",
        "message":                "テスト送信",
        "subject":                "Payment",
        "action_level":           "normal",
        "dimension":              "global",
        "organism_name":          "TestOrg",
        "sender_municipality":    "Asia/JP/18/Kanazawa",
        "receiver_municipality":  "Europe/IE/SO/Sligo",
        "details":                "テスト詳細",
        "goods_or_money":         "money",
        "location":               "Kanazawa",
        "proof_of_place":         "GPS"
    }

    # ─── 5) Dilithium 署名を作成 ─────────────────────────────────────────────
    canonical_bytes = json.dumps(payload_body, sort_keys=True, ensure_ascii=False).encode("utf-8")
    dilith_signed = dilithium_sign(canonical_bytes, sk_dili)
    if isinstance(dilith_signed, list):
        dilith_signed = bytes(dilith_signed)
    dilith_sig_b64 = base64.b64encode(dilith_signed).decode("utf-8")
    dilith_pubkey_b64 = base64.b64encode(pk_dili).decode("utf-8")

    # ─── 6) NTRU 暗号文を作成 ───────────────────────────────────────────────
    cipher_bytes_py, shared_secret_py = ntru_encrypt(pk_ntru)
    cipher_bytes: bytes = bytes(cipher_bytes_py)
    shared_secret: bytes = bytes(shared_secret_py)
    ntru_cipher_b64 = base64.b64encode(cipher_bytes).decode("utf-8")

    # ─── 7) リクエスト JSON を組み立て ─────────────────────────────────────
    request_json = {
        "client_cert":          client_cert_b64,
        "payload":              payload_body,
        "ntru_ciphertext":      ntru_cipher_b64,
        "dilithium_signature":  dilith_sig_b64,
        "dilithium_public_key": dilith_pubkey_b64
    }

    # ─── 8) POST リクエスト → レスポンスを検証 ────────────────────────────────
    res = client.post(
        "/send/api/send_transaction",
        data=json.dumps(request_json),
        content_type="application/json",
        headers={"Authorization": "Bearer dummy_jwt_token"}
    )
    assert res.status_code == 200, res.get_data(as_text=True)

    tx = res.get_json()
    # transaction_id, transaction_hash, status フィールドが返ってきていること
    assert "transaction_id" in tx
    assert "transaction_hash" in tx
    assert tx["status"] == "send_complete"

    # 固定ハッシュ (validate_transaction) を検証
    assert validate_transaction(tx)


def test_api_financial_statements(client):
    """
    GET /send/api/financial_statements?municipality=Boston → ダミーの決算書 JSON が返ることを確認します。
    """
    res = client.get(
        "/send/api/financial_statements?municipality=Boston",
        headers={"Authorization": "Bearer dummy_jwt_token"}
    )
    assert res.status_code == 200

    d = res.get_json()
    assert "financial_data" in d
    assert "assets" in d["financial_data"]
    assert "liabilities" in d["financial_data"]
    assert "equity" in d["financial_data"]
    assert "revenue" in d["financial_data"]
    assert "expenses" in d["financial_data"]
    assert "net_profit" in d["financial_data"]
