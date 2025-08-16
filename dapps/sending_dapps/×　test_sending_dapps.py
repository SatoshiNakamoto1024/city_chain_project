# dapps/sending_dapps/test_sending_dapps.py
# ================================================================
# sending_dapps 一式の統合テスト
#
# * city_dag_storage がまだ実装されていない環境でも失敗しないよう
#   import より“先”にスタブを sys.modules へ登録する。
# ================================================================

# ---------- 1) 先にスタブを注入 ---------- #
import sys, types, asyncio, uuid, logging

if "city_dag_storage" not in sys.modules:
    stub = types.ModuleType("city_dag_storage")

    class CityDAGStorage:                       # 実装が出来たら削除
        def __init__(self, *a, **kw):
            pass

        async def add_transaction(self, sender, receiver, amount, tx_type="send"):
            await asyncio.sleep(0)
            return f"dummy_{uuid.uuid4().hex[:8]}", f"dummy_hash_{uuid.uuid4().hex[:16]}"

    stub.CityDAGStorage = CityDAGStorage
    sys.modules["city_dag_storage"] = stub
# ------------------------------------------ #

# ---------- 2) パス調整 ---------- #
import os
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]      # city_chain_project/
sys.path.insert(0, str(PROJECT_ROOT / "dapps"))         # dapps パッケージ
sys.path.insert(0, str(PROJECT_ROOT))                   # プロジェクトルート
# ---------------------------------- #

# ---------- 3) 標準 / 外部 import ---------- #
import json
import base64
import pytest
from flask import Flask
import boto3
# ------------------------------------------- #

# ---------- 4) sending_dapps 関連 ---------- #
from sending_dapps.sending_dapps import send_bp
from sending_dapps.validator import validate_transaction
from sending_dapps.sending_dapps import (
    ntru_generate, ntru_encrypt, ntru_decrypt,
    dilithium_generate, dilithium_sign, dilithium_verify,
    get_wallet_by_user
)
# PEM 解析ユーティリティ（CA 側で用意済み）
from CA.client_cert_utils import extract_keys_from_pem
# ------------------------------------------- #

# ================================================================
# 以降はフィクスチャとテスト本体
# ================================================================

TEST_SENDER_UUID   = "uuid_fixture_sender"
TEST_RECEIVER_UUID = "uuid_fixture_receiver"

# ──────────────────────────── boto3 Dummy DynamoDB ───────────────
class DummyTable:
    def __init__(self):
        self.storage = {}

    def get_item(self, Key):
        return {"Item": self.storage.get((Key["uuid"], Key["session_id"]), {})}

    def put_item(self, Item, ReturnValues=None):
        self.storage[(Item["uuid"], Item["session_id"])] = Item
        return {}

class DummyDbResource:
    def __init__(self):
        self._tbl = DummyTable()

    def Table(self, *_):
        return self._tbl
# ----------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_boto3(monkeypatch):
    monkeypatch.setattr(boto3, "resource", lambda *a, **k: DummyDbResource())

@pytest.fixture(autouse=True)
def patch_verify_jwt(monkeypatch):
    monkeypatch.setattr(
        "sending_dapps.sending_dapps.verify_jwt",
        lambda _tok: {"user_uuid": TEST_SENDER_UUID}
    )

@pytest.fixture(autouse=True)
def patch_wallet(monkeypatch):
    class DummyWallet:
        wallet_address = "dummy_wallet"
        balance = "1000000"
    monkeypatch.setattr(
        "sending_dapps.sending_dapps.get_wallet_by_user",
        lambda _uuid: DummyWallet()
    )

@pytest.fixture
def client():
    app = Flask(__name__, template_folder="templates")
    app.register_blueprint(send_bp, url_prefix="/send")
    return app.test_client()

# ================================================================
# テスト：ユーザー一覧 API
# ================================================================
def test_api_list_users(client):
    res = client.get("/send/api/users?region=Asia")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) == 5
    assert all("uuid" in u and "username" in u for u in data)

# ================================================================
# テスト：send_transaction フロー
# ================================================================
def test_send_transaction_flow(client, monkeypatch):
    FIX = Path(__file__).with_suffix("").parent / "_fixtures"
    pem_path = FIX / "client.pem"

    # 1) PEM から鍵抽出
    ntru_pub, dil_pub = extract_keys_from_pem(pem_path)
    ntru_pub_b64      = base64.b64encode(ntru_pub).decode()
    dil_pub_b64       = base64.b64encode(dil_pub).decode()

    # 2) DynamoDB（Dummy）へ送信者レコード準備
    tbl = boto3.resource("dynamodb").Table("UsersTable")
    tbl.put_item(Item={
        "uuid": TEST_SENDER_UUID,
        "session_id": "USER_PROFILE",
        "username": "Fixture_User",
        "ntru_secret_key_b64": base64.b64encode(ntru_generate().secret_key).decode(),
        "dilithium_public_key": dil_pub_b64,
        "region": "Asia"
    })
    tbl.put_item(Item={
        "uuid": TEST_RECEIVER_UUID,
        "session_id": "USER_PROFILE",
        "username": "Fixture_Receiver"
    })

    # 3) 署名／暗号化
    payload_body = {
        "receiver_uuid": TEST_RECEIVER_UUID,
        "amount": "12.3",
        "message": "pytest flow",
        "subject": "Payment",
        "action_level": "normal",
        "dimension": "global",
        "organism_name": "TestOrg",
        "sender_municipality": "Asia/JP/18/Kanazawa",
        "receiver_municipality": "Asia/JP/18/Kanazawa",
        "details": "pytest details",
        "goods_or_money": "money",
        "location": "Kanazawa",
        "proof_of_place": "GPS"
    }
    canonical = json.dumps(payload_body, sort_keys=True, ensure_ascii=False).encode()
    pk_dil, sk_dil = dilithium_generate()
    sig_b64 = base64.b64encode(dilithium_sign(canonical, sk_dil)).decode()

    cipher, _shared = ntru_encrypt(ntru_pub)
    cipher_b64 = base64.b64encode(cipher).decode()

    # 4) リクエスト
    req = {
        "client_cert": base64.b64encode(pem_path.read_bytes()).decode(),
        "payload": payload_body,
        "ntru_ciphertext": cipher_b64,
        "dilithium_signature": sig_b64,
        "dilithium_public_key": dil_pub_b64
    }
    res = client.post("/send/api/send_transaction",
                      data=json.dumps(req),
                      content_type="application/json",
                      headers={"Authorization": "Bearer dummy"})
    assert res.status_code == 200, res.get_data(as_text=True)
    tx = res.get_json()
    assert tx["status"] == "send_complete"
    assert validate_transaction(tx)

# ================================================================
# テスト：ダミー決算書 API
# ================================================================
def test_financial_statements(client):
    res = client.get("/send/api/financial_statements?municipality=TestCity",
                     headers={"Authorization": "Bearer dummy"})
    assert res.status_code == 200
    js = res.get_json()
    assert "financial_data" in js
    assert set(js["financial_data"]).issuperset(
        {"assets", "liabilities", "equity", "revenue", "expenses", "net_profit"}
    )
