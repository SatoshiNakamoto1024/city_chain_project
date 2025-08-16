# File: dapps/sending_dapps/test_sending_dapps_static_pem.py
# ─────────────────────────────────────────────────────────────────────────────
# sending_dapps 統合テスト（あらかじめ CA 発行済みの PEM を読み込むパターン）
#
# 1) テスト冒頭で TEST_ENV=true をセット → cert_utils や verify_message_signature をバイパス
# 2) DummyTable に scan(), get_item(), put_item() を実装 (test_api_list_users 対応)
# 3) 既存の client PEM ファイルを load → 鍵を取り出す extract_keys_from_pem()
# 4) DynamoDB モックに登録して送信フローを回す
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import types
import asyncio
import uuid
import base64
import json
import pytest

# ─────────────────────────────────────────────────────────────────────────────
# テスト時はまず TEST_ENV=true をセットしておく（cert_utils や verify_message_signature がバイパスされる）
os.environ["TEST_ENV"] = "true"

# ─────────────────────────────────────────────────────────────────────────────
# プロジェクトルートを sys.path に追加 (city_chain_project/ 以下)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)              # city_chain_project/
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dapps"))  # dapps パッケージ

# ─────────────────────────────────────────────────────────────────────────────
# 事前に CA で発行した「クライアント証明書 PEM」を読み込むためのパス
# 例: CA/client_certs/client_demo_abcdef12.pem
CLIENT_PEM_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../CA/client_certs")),
    "client_demo_1f98bc2509db41339d45cee414506076.pem"  # ← 実際に存在するファイル名に合わせてください
)

# ─────────────────────────────────────────────────────────────────────────────
# pyasn1 を使って PEM から鍵を取り出すユーティリティ
from pyasn1.codec.der import decoder as der_decoder
from pyasn1_modules import rfc5280
from pyasn1.type import univ

def extract_keys_from_pem(pem_bytes: bytes):
    """
    pyasn1 を使い、PEM から
      - NTRU 公開鍵 (bytes)
      - Dilithium 公開鍵 (bytes)
    を取り出して返却します。
    """
    # PEM の余計な行を削って Base64 部分のみ連結し、DER 化
    lines = pem_bytes.splitlines()
    b64 = b"".join(line for line in lines if line and not line.startswith(b"-----"))
    der = base64.b64decode(b64)

    cert, _ = der_decoder.decode(der, asn1Spec=rfc5280.Certificate())
    tbs = cert["tbsCertificate"]
    spki = tbs.getComponentByName("subjectPublicKeyInfo")

    alg_oid = str(spki["algorithm"]["algorithm"])
    if alg_oid != "1.3.6.1.4.1.99999.1.0":
        raise ValueError(f"SPKI の algorithm OID が想定外: {alg_oid}")

    # NTRU 公開鍵は subjectPublicKey (BIT STRING) として格納されている
    ntru_pub = spki["subjectPublicKey"].asOctets()

    # parameters に OctetString(Dilithium 公開鍵) が DER エンコードされた形で入っている
    params_any = spki["algorithm"].getComponentByName("parameters")
    if not (params_any and params_any.isValue):
        raise ValueError("SPKI.parameters に Dilithium 公開鍵が見つかりません")
    octet, _ = der_decoder.decode(bytes(params_any), asn1Spec=univ.OctetString())
    dil_pub = octet.asOctets()

    return ntru_pub, dil_pub

# ─────────────────────────────────────────────────────────────────────────────
# Flask／boto3／sending_dapps インポート
from flask import Flask
import boto3
from boto3.dynamodb.conditions import Attr

from dapps.sending_dapps.sending_dapps import send_bp
from dapps.sending_dapps.validator import validate_transaction

# NTRU / Dilithium ラッパー (PyO3)
from dapps.sending_dapps.sending_dapps import (
    ntru_generate, ntru_encrypt, ntru_decrypt,
    dilithium_generate, dilithium_sign, dilithium_verify
)

# ─────────────────────────────────────────────────────────────────────────────
# テスト用ユーザー UUID（送信者・受信者）
TEST_SENDER_UUID   = "uuid_fixture_sender"
TEST_RECEIVER_UUID = "uuid_fixture_receiver"

# ─────────────────────────────────────────────────────────────────────────────
# pytest fixture: verify_jwt のモンキーパッチ
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def patch_verify_jwt(monkeypatch):
    """
    _process_sending_transaction() 内で使用している
        from login.auth_py.jwt_manager import verify_jwt
    を常に成功するようにモックします。
    """
    monkeypatch.setattr(
        "login.auth_py.jwt_manager.verify_jwt",
        lambda token: {"user_uuid": TEST_SENDER_UUID}
    )

# ─────────────────────────────────────────────────────────────────────────────
# pytest fixture: cert_utils の関数をすべてバイパス（TEST_ENV=true のおかげで
# verify_client_certificate() と verify_message_signature() は常に True を返しますが、
# 念のためにインポート先も直接モックしておきます）
# ─────────────────────────────────────────────────────────────────────────────
import dapps.sending_dapps.cert_utils as cert_utils
@pytest.fixture(autouse=True)
def patch_cert_utils(monkeypatch):
    monkeypatch.setattr(cert_utils, "verify_client_certificate", lambda cert: True)
    monkeypatch.setattr(cert_utils, "verify_message_signature", lambda msg, sig, pub: True)

# ─────────────────────────────────────────────────────────────────────────────
# pytest fixture: boto3.resource() をモック
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def patch_boto3_resource(monkeypatch):
    """
    boto3.resource() → DummyDynamoResource に置き換え、scan/get_item/put_item を実装します。
    """
    class DummyTable:
        def __init__(self):
            # (uuid, session_id) をキーに、それぞれ Item(dict) を保持
            self.storage = {
                # 送信者のユーザーレコード (USER_PROFILE)
                (TEST_SENDER_UUID, "USER_PROFILE"): {
                    "username": "Fixture_Sender",
                    # これらは後からテスト内でセットする
                    "ntru_secret_key_b64": "",
                    "dilithium_public_key": ""
                },
                # 受信者のユーザーレコード (USER_PROFILE)
                (TEST_RECEIVER_UUID, "USER_PROFILE"): {
                    "username": "Fixture_Receiver"
                }
            }

        def scan(self, FilterExpression=None):
            """
            api_list_users() の scan() 呼び出しに対応。
            region=Asia などでフィルタリングが入る想定ですが、テストでは返す Users を固定してよいので、
            適当に 5 レコード返します。
            """
            dummy_users = [
                {"uuid": f"dummy_uuid_a{i}", "username": f"dummy_user_a{i}", "region": "Asia", "sender_municipality": f"Asia/JP/City{i}"}
                for i in range(1, 6)
            ]
            return {"Items": dummy_users}

        def get_item(self, Key):
            """
            Key={"uuid": "...", "session_id": "..."} を受け取り、
            storage から取り出して {"Item": {...}} を返す。また uuid/session_id を戻り値に含める。
            """
            item = self.storage.get((Key["uuid"], Key["session_id"]))
            if item is None:
                return {}
            ret = item.copy()
            # put_item の前段階であっても、get_item の返却時点で uuid/session_id を埋めておく
            ret["uuid"]       = Key["uuid"]
            ret["session_id"] = Key["session_id"]
            return {"Item": ret}

        def put_item(self, Item, ReturnValues=None):
            """
            Item に "uuid","session_id" が含まれている想定で、storage を更新。
            """
            key = (Item["uuid"], Item["session_id"])
            # copy() しておかないと元データが壊れる恐れがあるので注意
            self.storage[key] = Item.copy()
            return {}

    class DummyDynamoResource:
        def __init__(self):
            self._singleton_table = DummyTable()

        def Table(self, name):
            return self._singleton_table

    monkeypatch.setattr(boto3, "resource", lambda *args, **kwargs: DummyDynamoResource())

# ─────────────────────────────────────────────────────────────────────────────
# pytest fixture: get_wallet_by_user() をモック
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def patch_get_wallet(monkeypatch):
    """
    _process_sending_transaction() の中で呼ばれる
      from login.wallet.wallet_service import get_wallet_by_user
    を常に残高十分な DummyWallet を返すようにします。
    """
    class DummyWallet:
        def __init__(self):
            self.wallet_address = "dummy_wallet_addr"
            self.balance = "1000000"

    monkeypatch.setattr(
        "login.wallet.wallet_service.get_wallet_by_user",
        lambda uuid: DummyWallet()
    )

# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def client():
    """
    Flask アプリを立ち上げ、send_bp を /send にマウントしたテストクライアントを返却します。
    """
    app = Flask(__name__, template_folder="templates")
    app.register_blueprint(send_bp, url_prefix="/send")
    return app.test_client()

# ─────────────────────────────────────────────────────────────────────────────
def test_api_list_users(client):
    """
    GET /send/api/users?region=Asia → scan() → 5 件のダミーユーザーが返ることを確認
    """
    res = client.get("/send/api/users?region=Asia")
    assert res.status_code == 200

    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) == 5
    for u in data:
        assert "uuid" in u
        assert "username" in u
        assert u.get("region") == "Asia"

# ─────────────────────────────────────────────────────────────────────────────
def test_send_transaction_and_validate(client):
    """
　  POST /send/api/send_transaction のフローが正しく動作し、かつ戻り値 tx の固定ハッシュ検証が通ることを確認します。
    """

    # 1) 既存の client PEM を読み込む
    with open(CLIENT_PEM_PATH, "rb") as f:
        client_pem = f.read()

    # 2) PEM から NTRU 公開鍵・Dilithium 公開鍵を抽出
    ntru_pub_bytes, dilith_pub_bytes = extract_keys_from_pem(client_pem)

    # 3) DynamoDB モックに送信者レコードを put_item
    dyn = boto3.resource("dynamodb")
    tbl = dyn.Table("UsersTable")
    sender_record = tbl.get_item(Key={"uuid": TEST_SENDER_UUID, "session_id": "USER_PROFILE"})["Item"]
    # (a) NTRU 秘密鍵はテスト用に新たに生成し、Base64 エンコードして格納
    kp_ntru = ntru_generate()
    sk_ntru = bytes(kp_ntru.secret_key)
    sender_record["ntru_secret_key_b64"]   = base64.b64encode(sk_ntru).decode("utf-8")
    # (b) Dilithium 公開鍵は PEM から取り出したものを Base64 エンコードして格納
    sender_record["dilithium_public_key"]  = base64.b64encode(dilith_pub_bytes).decode("utf-8")
    # ここで改めて uuid/session_id をセットしておく
    sender_record["uuid"]       = TEST_SENDER_UUID
    sender_record["session_id"] = "USER_PROFILE"
    tbl.put_item(Item=sender_record)

    # 4) Dilithium 鍵ペアを生成し、署名も作成
    _, sk_dili_raw = dilithium_generate()
    sk_dili = bytes(sk_dili_raw)
    # ※ ここでは本来「pem から取り出した Dilithium 公開鍵」を検証に使うので、
    #    署名検証自体は TEST_ENV=true によってバイパスされます。

    # 5) ダミーの client_cert.pem を Base64 化
    client_cert_b64 = base64.b64encode(client_pem).decode("utf-8")

    # 6) payload_body を準備（必須フィールドすべて含む）
    payload_body = {
        "receiver_uuid":         TEST_RECEIVER_UUID,
        "amount":                "42.0",
        "message":               "テスト送信",
        "subject":               "Payment",
        "action_level":          "normal",
        "dimension":             "global",
        "organism_name":         "TestOrg",
        "sender_municipality":   "Asia/JP/CityX",
        "receiver_municipality": "Europe/IE/CityY",
        "details":               "テスト詳細",
        "goods_or_money":        "money",
        "location":              "Kanazawa",
        "proof_of_place":        "GPS"
    }

    # 7) Dilithium 署名を生成
    canonical_bytes = json.dumps(payload_body, sort_keys=True, ensure_ascii=False).encode("utf-8")
    dilith_sig = dilithium_sign(canonical_bytes, sk_dili)
    if isinstance(dilith_sig, list):
        dilith_sig = bytes(dilith_sig)
    dilith_sig_b64   = base64.b64encode(dilith_sig).decode("utf-8")
    # 公開鍵はあくまで PEM から取り出したものを使うので、
    dilith_pubkey_b64 = base64.b64encode(dilith_pub_bytes).decode("utf-8")

    # 8) NTRU 暗号文を生成 （PEM から取り出した NTRU 公開鍵を使う）
    cipher_bytes_py, shared_secret_py = ntru_encrypt(ntru_pub_bytes)
    cipher_bytes  = bytes(cipher_bytes_py)
    shared_secret = bytes(shared_secret_py)
    ntru_cipher_b64 = base64.b64encode(cipher_bytes).decode("utf-8")

    # 9) リクエスト JSON を組み立て
    request_json = {
        "client_cert":          client_cert_b64,
        "payload":              payload_body,
        "ntru_ciphertext":      ntru_cipher_b64,
        "dilithium_signature":  dilith_sig_b64,
        "dilithium_public_key": dilith_pubkey_b64
    }

    # 10) POST 実行 → レスポンスを検証
    res = client.post(
        "/send/api/send_transaction",
        data=json.dumps(request_json),
        content_type="application/json",
        headers={"Authorization": "Bearer dummy_jwt_token"}
    )
    assert res.status_code == 200, res.get_data(as_text=True)

    tx = res.get_json()
    assert "transaction_id"   in tx
    assert "transaction_hash" in tx
    assert tx["status"] == "send_complete"
    assert validate_transaction(tx)

# ─────────────────────────────────────────────────────────────────────────────
def test_api_financial_statements(client):
    """
    GET /send/api/financial_statements?municipality=CityA → ダミー決算書が返ることを確認
    """
    res = client.get(
        "/send/api/financial_statements?municipality=CityA",
        headers={"Authorization": "Bearer dummy_jwt_token"}
    )
    assert res.status_code == 200
    d = res.get_json()
    assert "financial_data" in d
    assert set(d["financial_data"].keys()) >= {
        "assets", "liabilities", "equity", "revenue", "expenses", "net_profit"
    }
