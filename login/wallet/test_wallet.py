# login/wallet/test_wallet.py
"""
────────────────────────────────────────
pytest で実行すると、実 DynamoDB の WalletsTable を相手に

 1. create_wallet_for_user
 2. get_wallet_by_user
 3. increment_balance
 4. Flask ルート /wallet/me と /wallet/adjust

をまとめて検証する。本番テーブルを弄るため、最後に必ず掃除を行う。
"""
import sys, os, uuid, logging
from decimal import Decimal
import boto3, pytest
from flask import Flask

# テスト実行時に project root をパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from login.wallet.wallet_service import create_wallet_for_user, get_wallet_by_user, get_wallet, increment_balance
from login.wallet.wallet_routes  import wallet_bp
from login.wallet.config         import WALLET_TABLE, AWS_REGION
from login.wallet.wallet_db      import table as wallet_table

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(asctime)s %(message)s"
)

# テスト用ダミーユーザー
TEST_USER_UUID = f"test-{uuid.uuid4()}"
_created_wallets = []

def _dynamodb_available():
    try:
        boto3.client("dynamodb", region_name=AWS_REGION).describe_table(
            TableName=WALLET_TABLE)
        return True
    except Exception as e:
        logging.error("DynamoDB 接続/テーブル確認に失敗: %s", e)
        return False

pytestmark = pytest.mark.skipif(
    not _dynamodb_available(),
    reason="DynamoDB へ接続できないか WalletsTable が無い"
)

@pytest.fixture(scope="module")
def flask_client():
    app = Flask(__name__)
    app.register_blueprint(wallet_bp)
    return app.test_client()

def test_service_crud():
    # a) 新規 or 既存ウォレット取得
    w = create_wallet_for_user(TEST_USER_UUID)
    _created_wallets.append(w.wallet_address)
    assert w.user_uuid == TEST_USER_UUID
    assert w.balance == 0.0

    # b) GSI で取得
    w2 = get_wallet_by_user(TEST_USER_UUID)
    assert w2.wallet_address == w.wallet_address

    # c) 残高 +150.5
    bal1 = increment_balance(w.wallet_address, 150.5)
    assert bal1 == pytest.approx(150.5)

    # d) 残高 -50
    bal2 = increment_balance(w.wallet_address, -50)
    assert bal2 == pytest.approx(100.5)

    # e) 直接取得
    w_final = get_wallet(w.wallet_address)
    assert w_final.balance == pytest.approx(100.5)

def _fake_verify_jwt(_token):
    return {"uuid": TEST_USER_UUID}

def test_flask_routes(monkeypatch, flask_client):
    monkeypatch.setattr("login.wallet.wallet_routes.verify_jwt", _fake_verify_jwt)

    # GET /wallet/me
    res = flask_client.get("/wallet/me", headers={"Authorization": "Bearer dummy"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["wallet_address"].startswith("wallet-")
    assert body["balance"] == pytest.approx(100.5)

    # POST /wallet/adjust
    res2 = flask_client.post("/wallet/adjust", json={
        "wallet_address": body["wallet_address"],
        "delta": 25.0
    })
    assert res2.status_code == 200
    body2 = res2.get_json()
    assert body2["balance"] == pytest.approx(125.5)

def teardown_module(_):
    # テストで作ったウォレットを削除
    for addr in _created_wallets:
        try:
            wallet_table.delete_item(Key={"wallet_address": addr})
            logging.info("Deleted test wallet %s", addr)
        except Exception as e:
            logging.error("cleanup failed: %s", e)
