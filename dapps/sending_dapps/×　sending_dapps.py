# dapps/sending_dapps/sending_dapps.py
"""
sending_dapps Blueprint – 本番想定・500 ms 以内処理
"""

from __future__ import annotations
import os, sys, json, uuid, asyncio, base64, hashlib, logging
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify

# ── Paths & PQC libs ───────────────────────────────────────────
# このスクリプトが置かれているディレクトリ: dapps/sending_dapps
sys.path += [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),  # → project root
    r"D:\city_chain_project\ntru\ntru-py",
    r"D:\city_chain_project\ntru\dilithium-py",
]
from app_dilithium    import verify_message
from ntrust_native_py import (                      # ← NTRU Rust ラッパ (本番用)
    generate_keypair as ntru_generate,
    encrypt         as ntru_encrypt,
    decrypt         as ntru_decrypt,
)
from dilithium5 import (                            # ← Dilithium5 (本番用)
    generate_keypair as dilithium_generate,
    sign            as dilithium_sign,
    verify          as dilithium_verify,
)

# login_app 以下を import できるように project root が sys.path に入っていれば OK
from login.auth_py.jwt_manager     import verify_jwt
from login.wallet.wallet_service    import get_wallet_by_user
from sending_dapps.cert_utils      import (
    verify_client_certificate,
    verify_message_signature
)
from sending_dapps.cert_cache      import get_cached_secret, put_cached_secret
from sending_dapps.region_registry import get_region_config

import boto3
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AWS_REGION  = os.getenv("AWS_REGION", "us-east-1")
USERS_TABLE = os.getenv("USERS_TABLE", "UsersTable")

# CityDAGHandler – ネットワーク層
try:
    from network.sending_DAG.python_sending.city_level.city_dag_handler import CityDAGHandler
except ImportError:
    logger.warning("CityDAGHandler がインポートできなかったため、ダミー実装を使用します。")
    # ダミー版コンストラクタは city_name 1 引数を想定しておく
    class CityDAGHandler:
        def __init__(self, city_name: str, *args, **kwargs):
            self.city_name = city_name

        async def add_transaction(self, sender, receiver, amount, tx_type="send"):
            dummy_id   = "dummy_tx_id_" + uuid.uuid4().hex[:8]
            dummy_hash = "dummy_hash_"   + uuid.uuid4().hex[:16]
            return (dummy_id, dummy_hash)

send_bp = Blueprint("send_bp", __name__, template_folder="templates")


# ========== HTML フォーム ========== #
@send_bp.route("/", methods=["GET"])
def form():
    return render_template(
        "send_screen.html",
        wallet_address=request.args.get("wallet", "unknown"),
        balance=request.args.get("balance", "0.00")
    )


# ========== ユーザー一覧 ========== #
@send_bp.route("/api/users", methods=["GET"])
def api_users():
    region       = request.args.get("region")
    municipality = request.args.get("municipality")

    tbl = boto3.resource("dynamodb", region_name=AWS_REGION).Table(USERS_TABLE)
    if municipality:
        resp = tbl.scan(FilterExpression=Attr("sender_municipality").eq(municipality))
    elif region:
        resp = tbl.scan(FilterExpression=Attr("region").eq(region))
    else:
        resp = tbl.scan()

    items = resp.get("Items", []) or []
    # 必要なフィールドのみ返す
    users = []
    for i in items:
        if "uuid" in i and "username" in i:
            users.append({
                "uuid":         i["uuid"],
                "username":     i["username"],
                "municipality": i.get("sender_municipality", "")
            })
    return jsonify(users)


# ========== 送信 ========== #
@send_bp.route("/api/send_transaction", methods=["POST"])
def api_send():
    # --- 1) JWT で送信者を復元 ----------------------------
    auth_hdr = request.headers.get("Authorization", "")
    token    = auth_hdr.split()[-1]  # "Bearer XXX"
    jwt_payload = verify_jwt(token)
    sender_uuid  = jwt_payload.get("uuid") or jwt_payload.get("user_uuid")
    if not sender_uuid:
        return jsonify({"error": "invalid JWT"}), 400

    # --- 2) リクエスト JSON 取得 --------------------------
    data          = request.get_json(force=True)
    client_pem_b64 = data.get("client_cert", "")
    payload        = data.get("payload", {})
    cipher_b64     = data.get("ntru_ciphertext", "")
    sig_b64        = data.get("dilithium_signature", "")
    dili_pub_b64   = data.get("dilithium_public_key", "")

    # 必須チェック
    if not (client_pem_b64 and payload and cipher_b64 and sig_b64 and dili_pub_b64):
        return jsonify({"error": "missing fields"}), 400

    # --- 3) クライアント証明書検証（PEM→NTRU+Dilithium を検証） -------
    try:
        pem_bytes = base64.b64decode(client_pem_b64)
    except Exception:
        return jsonify({"error": "client_cert is not valid Base64"}), 400

    if not verify_client_certificate(pem_bytes):
        return jsonify({"error": "cert verify failed"}), 400

    # --- 4) DynamoDB から sender / receiver を取得 -----------------
    table = boto3.resource("dynamodb", region_name=AWS_REGION).Table(USERS_TABLE)
    try:
        sender_item   = table.get_item(Key={"uuid": sender_uuid, "session_id": "USER_PROFILE"})["Item"]
        receiver_item = table.get_item(Key={"uuid": payload["receiver_uuid"], "session_id": "USER_PROFILE"})["Item"]
    except KeyError:
        return jsonify({"error": "sender or receiver not found"}), 400

    # --- 5) Dilithium 署名検証 -----------------------------------
    # 送信側が payload を JSON.stringify(sortKeys) してサーバーに送ってくる、
    # サーバー側では同じソート順で canonical JSON を再現してバイト列化してから検証する
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    try:
        sig_bytes   = base64.b64decode(sig_b64)
        pubkey_bytes = base64.b64decode(dili_pub_b64)
    except Exception:
        return jsonify({"error": "signature or public_key not valid Base64"}), 400

    # フロントの署名付き公開鍵と、DynamoDB 登録済みの公開鍵を突合する
    registered_dili_pub = sender_item.get("dilithium_public_key", "")
    if registered_dili_pub != dili_pub_b64:
        return jsonify({"error": "mismatched dilithium public_key"}), 400

    if not verify_message_signature(canonical, sig_bytes, pubkey_bytes):
        return jsonify({"error": "signature verify failed"}), 400

    # --- 6) NTRU 復号 → shared_secret（キャッシュ対応） --------------
    try:
        cipher_bytes = base64.b64decode(cipher_b64)
    except Exception:
        return jsonify({"error": "ntru_ciphertext not valid Base64"}), 400

    secret = get_cached_secret(cipher_bytes)
    if secret is None:
        try:
            sk_bytes = base64.b64decode(sender_item["ntru_secret_key_b64"])
        except Exception:
            return jsonify({"error": "invalid ntru_secret_key stored"}), 400

        try:
            shared_secret = ntru_decrypt(cipher_bytes, sk_bytes)
        except Exception as e:
            return jsonify({"error": f"ntru decryption failed: {e}"}), 400

        # 復号に成功したらキャッシュに入れておく
        put_cached_secret(cipher_bytes, shared_secret)
    else:
        shared_secret = secret

    # --- 7) ウォレット残高チェック --------------------------------
    try:
        amount = float(payload["amount"])
    except Exception:
        return jsonify({"error": "amount must be numeric"}), 400

    wallet_obj = get_wallet_by_user(sender_uuid)
    if not wallet_obj or float(wallet_obj.balance) < amount:
        return jsonify({"error": "balance low"}), 400

    # --- 8) トランザクションオブジェクトを構築＆ハッシュ計算 ----------
    tx_id = str(uuid.uuid4())
    now   = datetime.now(timezone.utc).isoformat()
    tx = {
        "transaction_id": tx_id,
        "timestamp":      now,
        "sender":         sender_item["username"],
        "receiver":       receiver_item["username"],
        "amount":         amount,
        "payload":        payload,
        "status":         "pending"
    }
    tx["transaction_hash"] = hashlib.sha256(
        json.dumps(tx, sort_keys=True).encode("utf-8")
    ).hexdigest()

    # --- 9) 非同期で DAG に飛ばしつつ、DynamoDB にも書き込む ------------
    async def dag_write():
        # CityDAGHandler の本来シグネチャは __init__(self, city_name)
        city_name = sender_item.get("region", "Default")
        h = CityDAGHandler(city_name)
        return await h.add_transaction(tx["sender"], tx["receiver"], amount)

    async def dynamo_write():
        hist_item = {
            "uuid":           str(uuid.uuid4()),
            "session_id":     "TX_HISTORY",
            "transaction_id": tx_id,
            "sender_uuid":    sender_uuid,
            "receiver_uuid":  receiver_item["uuid"],
            "amount":         str(amount),
            "timestamp":      now,
            "status":         "send_complete"
        }
        table.put_item(Item=hist_item)

    # asyncio.run の中で両方を並列実行
    asyncio.run(asyncio.gather(dag_write(), dynamo_write()))

    tx["status"] = "send_complete"
    return jsonify(tx)
