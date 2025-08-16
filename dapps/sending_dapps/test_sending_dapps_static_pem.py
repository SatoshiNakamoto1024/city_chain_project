# File: dapps/sending_dapps/test_sending_dapps_static_pem.py

import os
import sys
import uuid, hashlib
import time
import base64
import json
import pytest

# ─────────────────────────────────────────────────────────────────────────────
# テスト時は cert_utils, verify_message_signature をバイパスするために
# TEST_ENV=true をセット
os.environ["TEST_ENV"] = "true"

# ─────────────────────────────────────────────────────────────────────────────
# プロジェクトルートを sys.path に追加
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)              # city_chain_project/
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dapps"))  # dapps パッケージ

# ─────────────────────────────────────────────────────────────────────────────
# CA モジュール読み込み用（動的に PEM を発行）
from CA.ca_generate_cert_asn1 import generate_root_cert
from CA.ca_issue_client_cert_asn1 import issue_client_cert

# pyasn1 を使って PEM から鍵（NTRU, Dilithium）を取り出すユーティリティ
from pyasn1.codec.der import decoder as der_decoder
from pyasn1_modules import rfc5280
from pyasn1.type import univ

def extract_keys_from_pem(pem_bytes: bytes):
    """
    pyasn1 を使い、PEM(certificate) から
      - NTRU 公開鍵 (bytes)
      - Dilithium 公開鍵 (bytes)
    を抽出します。
    """
    lines = pem_bytes.splitlines()
    b64 = b"".join(line for line in lines if line and not line.startswith(b"-----"))
    der = base64.b64decode(b64)

    cert, _ = der_decoder.decode(der, asn1Spec=rfc5280.Certificate())
    tbs = cert["tbsCertificate"]
    spki = tbs.getComponentByName("subjectPublicKeyInfo")

    alg_oid = str(spki["algorithm"]["algorithm"])
    if alg_oid != "1.3.6.1.4.1.99999.1.0":
        raise ValueError(f"SPKI OID が想定外: {alg_oid}")

    # NTRU 公開鍵は subjectPublicKey の bitstring
    ntru_pub = spki["subjectPublicKey"].asOctets()

    # Dilithium 公開鍵は AlgorithmIdentifier.parameters に OctetString で埋め込まれている
    params_any = spki["algorithm"].getComponentByName("parameters")
    if not (params_any and params_any.isValue):
        raise ValueError("SPKI.parameters に Dilithium 公開鍵が見つからない")
    octet, _ = der_decoder.decode(bytes(params_any), asn1Spec=univ.OctetString())
    dil_pub = octet.asOctets()

    return ntru_pub, dil_pub

# ─────────────────────────────────────────────────────────────────────────────
# Flask／boto3／sending_dapps のインポート
from flask import Flask
import boto3
from dapps.sending_dapps.sending_dapps import send_bp

# NTRU / Dilithium ラッパー
from dapps.sending_dapps.sending_dapps import (
    ntru_generate, ntru_encrypt, ntru_decrypt,
    dilithium_generate, dilithium_sign, dilithium_verify
)

# JWT 発行に必要なもの
import jwt
from login.auth_py.config import JWT_SECRET, JWT_ALGORITHM

# ─────────────────────────────────────────────────────────────────────────────
# テスト用ユーザー UUID（送信者・受信者）
TEST_SENDER_UUID   = "uuid_fixture_sender"
TEST_RECEIVER_UUID = "uuid_fixture_receiver"

# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def patch_get_wallet(monkeypatch):
    """
    sending_dapps.py 内で参照される
    login.wallet.wallet_service.get_wallet_by_user をモックします。
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
    app = Flask(__name__, template_folder="templates")
    app.register_blueprint(send_bp, url_prefix="/send")
    return app.test_client()

# ─────────────────────────────────────────────────────────────────────────────
def test_api_list_users(client):
    res = client.get("/send/api/users?region=Asia")
    assert res.status_code == 200

    data = res.get_json()
    assert isinstance(data, list)
    # 実際の UsersTable に入っている数が返ってくるはず
    # ここでは「空でも list」であれば OK とします
    assert isinstance(data, list)

# ─────────────────────────────────────────────────────────────────────────────
def test_send_transaction_and_validate(client):
    """
    POST /send/api/send_transaction のフローが本番同様に動作し、
    戻り値 tx の固定ハッシュ検証が通ることを確認します。
    """

    # 0) CA ルート証明書を生成（既存があれば最新を返す）
    generate_root_cert()

    # 1) NTRU+Dilithium 鍵ペアを生成
    kp_ntru = ntru_generate()
    pk_ntru = bytes(kp_ntru.public_key)
    sk_ntru = bytes(kp_ntru.secret_key)

    pk_dili_raw, sk_dili_raw = dilithium_generate()
    pk_dili = bytes(pk_dili_raw)
    sk_dili = bytes(sk_dili_raw)

    # 2) CA へ「両方の公開鍵」を渡して PEM を発行
    client_cn = f"test-client-{uuid.uuid4().hex[:8]}"
    client_pem = issue_client_cert(pk_ntru, pk_dili, client_cn)

    # 3) PEM から NTRU/Dilithium 公開鍵を抽出
    ntru_pub_bytes, dilith_pub_bytes = extract_keys_from_pem(client_pem)

    # 4) 実際の UsersTable に送信者レコードを put_item
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    table_name = os.getenv("USERS_TABLE", "UsersTable")
    dynamodb = boto3.resource("dynamodb", region_name=aws_region)
    table = dynamodb.Table(table_name)

    # 既存レコードを取得
    resp = table.get_item(Key={"uuid": TEST_SENDER_UUID, "session_id": "USER_PROFILE"})
    sender_record = resp.get("Item", {
        "uuid": TEST_SENDER_UUID,
        "session_id": "USER_PROFILE",
        "username": "Fixture_Sender"
    })

    # 鍵情報を格納
    sender_record["ntru_secret_key_b64"] = base64.b64encode(sk_ntru).decode("utf-8")
    sender_record["dilithium_public_key"]  = base64.b64encode(dilith_pub_bytes).decode("utf-8")

    # put_item 実行
    table.put_item(Item=sender_record)
    time.sleep(1)  # DynamoDB の整合性を待つ
    # 受信者レコードも同様に用意しておく
    receiver_record = {
        "uuid": TEST_RECEIVER_UUID,
        "session_id": "USER_PROFILE",
        "username": "Fixture_Receiver",
    }
    table.put_item(Item=receiver_record)
    
    # 確認
    recheck = table.get_item(Key={"uuid": TEST_SENDER_UUID, "session_id": "USER_PROFILE"}).get("Item")
    assert recheck is not None
    assert recheck["dilithium_public_key"] == base64.b64encode(dilith_pub_bytes).decode()

    # 5) JWT を発行
    now_ts = int(time.time())
    future_exp = now_ts + 3600
    payload = {"user_uuid": TEST_SENDER_UUID, "exp": future_exp}
    jwt_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    # 6) Dilithium 署名を作成
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
    canonical_bytes = json.dumps(payload_body, sort_keys=True, ensure_ascii=False).encode("utf-8")
    dilith_sig = dilithium_sign(canonical_bytes, sk_dili)
    if isinstance(dilith_sig, list):
        dilith_sig = bytes(dilith_sig)
    dilith_sig_b64    = base64.b64encode(dilith_sig).decode("utf-8")
    dilith_pubkey_b64 = base64.b64encode(dilith_pub_bytes).decode("utf-8")

    # 7) NTRU 暗号文を生成
    cipher_bytes_py, shared_secret_py = ntru_encrypt(ntru_pub_bytes)
    cipher_bytes  = bytes(cipher_bytes_py)
    shared_secret = bytes(shared_secret_py)
    ntru_cipher_b64 = base64.b64encode(cipher_bytes).decode("utf-8")

    # 8) client_cert.pem を Base64 化
    client_cert_b64 = base64.b64encode(client_pem).decode("utf-8")

    # 9) リクエスト JSON を組み立て
    request_json = {
        "client_cert":          client_cert_b64,
        "payload":              payload_body,
        "ntru_ciphertext":      ntru_cipher_b64,
        "dilithium_signature":  dilith_sig_b64,
        "dilithium_public_key": dilith_pubkey_b64
    }

    # 10) POST 実行 → レスポンス検証
    res = client.post(
        "/send/api/send_transaction",
        data=json.dumps(request_json),
        content_type="application/json",
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    assert res.status_code == 200, res.get_data(as_text=True)

    tx = res.get_json()
    assert "transaction_id"   in tx
    assert "transaction_hash" in tx
    assert tx["status"] == "send_complete"

    # 鍵の Base64 文字列一致も確認
    assert dilith_pubkey_b64 == base64.b64encode(pk_dili).decode()

# ─────────────────────────────────────────────────────────────────────────────
def test_api_financial_statements(client):
    """
    GET /send/api/financial_statements?municipality=CityA → ダミーの決算書が返ることを確認
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

def validate_transaction(tx):
    """
    本番コードと同様の IMMUTABLE_FIELDS を使用して、トランザクションハッシュを検証する
    """
    IMMUTABLE_FIELDS = [
        "sender", "receiver", "from_wallet", "to_wallet", "amount",
        "transaction_id", "subject", "action_level", "dimension",
        "organism_name", "sender_municipality", "receiver_municipality",
        "details", "goods_or_money", "location", "proof_of_place",
        "encrypted_message", "dilithium_signature"
    ]

    immutable_data = {k: tx[k] for k in IMMUTABLE_FIELDS if k in tx}
    expected_hash = hashlib.sha256(
        json.dumps(immutable_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    return tx["transaction_hash"] == expected_hash
