# File: dapps/sending_dapps/sending_dapps.py

"""
sending_dapps Blueprint  — 本番環境想定・PQC-OID 検証対応版

- GET  /send/                         → 送信用フォームを返す
- GET  /send/api/users                → DynamoDB から登録ユーザー一覧を返す
- POST /send/api/send_transaction     → トランザクション生成＋DAG登録（PQC 証明書検証＋署名検証）
- GET  /send/api/financial_statements → テスト用ダミーの決算書データを返す
"""

import os
import sys
import json
import uuid
import logging
import asyncio
import random
import hashlib
import base64
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, jsonify
import boto3
from boto3.dynamodb.conditions import Attr

# ──────────── プロジェクトパス調整 ────────────
# このファイルは「dapps/sending_dapps/sending_dapps.py」に配置されている想定で、
# プロジェクト直下（city_chain_project）や dapps パッケージを import 可能にします。
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)              # city_chain_project/
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dapps"))  # dapps パッケージ

# JWT 検証用ユーティリティをインポート
from login.auth_py.jwt_manager import verify_jwt

# ────────── 本番実装：NTRU／Dilithium ラッパー読み込み ──────────
# 例: PyO3 ビルド済みモジュールが下記フォルダにある想定
sys.path.append(r"D:\city_chain_project\ntru\ntru-py")       # NTRU PyO3
sys.path.append(r"D:\city_chain_project\ntru\dilithium-py")  # Dilithium PyO3

try:
    import ntrust_native_py       # NTRU KEM: generate_keypair, encrypt, decrypt
    from ntrust_native_py import generate_keypair as ntru_generate, \
                                    encrypt as ntru_encrypt, \
                                    decrypt as ntru_decrypt
except ImportError:
    raise ImportError("ntru-py (ntrust_native_py) が import できません。ビルドを確認してください。")

try:
    import dilithium5             # Dilithium‐5: generate_keypair, sign, verify
    from dilithium5 import generate_keypair as dilithium_generate, \
                             sign as dilithium_sign, \
                             verify as dilithium_verify
except ImportError:
    raise ImportError("dilithium-py (dilithium5) が import できません。ビルドを確認してください。")

# ────────── PQC 証明書検証ユーティリティを import ──────────
from sending_dapps.cert_utils import (
    verify_client_certificate,
    verify_message_signature
)

# ────────── 大陸別 DAG サーバー設定を取得 ──────────
from sending_dapps.region_registry import get_region_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB の設定値（環境変数またはデフォルト）
AWS_REGION  = os.getenv("AWS_REGION", "us-east-1")
USERS_TABLE = os.getenv("USERS_TABLE", "UsersTable")

send_bp = Blueprint("send_bp", __name__, template_folder="templates")


# ──── CityDAGHandler のインポートをスタブ可能にする ────
try:
    from network.sending_DAG.python_sending.city_level.city_dag_handler import CityDAGHandler
except ImportError:
    logger.warning("CityDAGHandler がインポートできなかったため、ダミー実装を使用します。")
    class CityDAGHandler:
        def __init__(self, *args, **kwargs):
            pass

        async def add_transaction(self, sender, receiver, amount, tx_type="send"):
            dummy_id = "dummy_tx_id_" + uuid.uuid4().hex[:8]
            dummy_hash = "dummy_hash_" + uuid.uuid4().hex[:16]
            return (dummy_id, dummy_hash)
# ────────────────────────────────────────────────────────────


@send_bp.route("/", methods=["GET"])
def send_form():
    """
    ブラウザから /send/ を開いたときに send_screen.html を返す。
    クエリパラメータで wallet, balance を受け取れる。
    """
    wallet  = request.args.get("wallet", "N/A")
    balance = request.args.get("balance", "0.00")
    return render_template("send_screen.html",
                           wallet_address=wallet,
                           balance=balance)


@send_bp.route("/api/users", methods=["GET"])
def api_list_users():
    """
    登録済みユーザー一覧を返却します。
    - ?region=Asia の場合：region フィールドでフィルタした結果を返す
    - ?municipality=XXX の場合：sender_municipality でフィルタ
    - どちらもない場合はテーブル全体を返す
    """
    region       = request.args.get("region")
    municipality = request.args.get("municipality")

    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(USERS_TABLE)

        # --- scan → 全アイテム取得して Python 側でフィルタをかける ---
        resp = table.scan()
        items = resp.get("Items", []) or []

        # municipality が指定されていればそちらで絞り込み
        if municipality:
            filtered = [u for u in items if u.get("sender_municipality") == municipality]
        # region が指定されていれば region フィールドで絞り込み
        elif region:
            filtered = [u for u in items if u.get("region") == region]
        else:
            filtered = items

        # レスポンス用に必要なフィールドだけ取り出す
        users = []
        for u in filtered:
            if "uuid" in u and "username" in u:
                users.append({
                    "uuid":         u["uuid"],
                    "username":     u["username"],
                    "municipality": u.get("sender_municipality", ""),
                    "region":       u.get("region", "")
                })
        return jsonify(users), 200

    except Exception as e:
        logger.exception("api_list_users error")
        return jsonify({"error": str(e)}), 500


@send_bp.route("/api/send_transaction", methods=["POST"])
def api_send_transaction():
    """
    トランザクション生成 → DAG 登録（本番実装用）

    Authorization: Bearer <JWT> ヘッダを必須とする

    クライアントから次の JSON を受け取る想定：
    {
      "client_cert":           "<Base64 PEM 形式の client_cert.pem>",
      "payload":               { … 実際に送信したい項目 … },
      "ntru_ciphertext":       "<Base64 エンコードされた NTRU 暗号文>",
      "dilithium_signature":   "<Base64 エンコードされた Dilithium 署名>",
      "dilithium_public_key":  "<Base64 エンコードされた Dilithium 公開鍵>"
    }
    """
    auth_hdr = request.headers.get("Authorization", "")
    jwt_token = auth_hdr.replace("Bearer ", "").strip()
    j = request.get_json(force=True) or {}

    try:
        tx = asyncio.run(_process_sending_transaction(j, jwt_token))
        return jsonify(tx), 200
    except Exception as e:
        logger.exception("send_transaction error")
        return jsonify({"error": str(e)}), 400


@send_bp.route("/api/financial_statements", methods=["GET"])
def api_financial_statements():
    """
    テスト用ダミー決算書データを返却
    ?municipality=CityA
    """
    muni = request.args.get("municipality", "unknown")
    rand = lambda: round(random.uniform(1000, 5000), 2)
    data = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "municipality": muni,
        "financial_data": {
            "assets":      rand(),
            "liabilities": rand(),
            "equity":      rand(),
            "revenue":     rand(),
            "expenses":    rand(),
            "net_profit":  rand()
        }
    }
    return jsonify(data), 200


async def _process_sending_transaction(data: dict, jwt_token: str) -> dict:
    """
    実際のトランザクション生成処理 (本番実装用)：
     1) JWT → 送信者ユーザー検証
     2) クライアント証明書 (client_cert) の検証（PQC-OID 対応版）
     3) Dilithium 署名検証
     4) NTRU 復号して「共通鍵」を取得
     5) 必須フィールドチェック
     6) ウォレット残高チェック & 受信者ウォレット存在チェック
     7) 固定ハッシュ計算 (Immutable Fields)
     8) CityDAGHandler へキューイング (非同期)
     9) DynamoDB への書き込み (バックグラウンド)
     10) レスポンス返却
    """

    # ── 1) JWT デコード & 送信者確認 ───────────────────────────────────
    # sending_dapps.py 内部では既にインポート済みの verify_jwt を呼ぶ
    payload = verify_jwt(jwt_token)
    sender_uuid = payload.get("user_uuid") or payload.get("uuid")
    # print群を追加してチェック
    print(" JWT payload:", payload)
    print(" JWTから取り出した sender_uuid:", sender_uuid)
    if not sender_uuid:
        raise ValueError("JWT に user_uuid が含まれていません")

    # DynamoDB から送信者情報取得（鍵類を取得するため）
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(USERS_TABLE)
    sender_item = table.get_item(Key={"uuid": sender_uuid, "session_id": "USER_PROFILE"}).get("Item")
    # print群を追加してチェック
    print(f" DynamoDB Lookup Key → uuid: {sender_uuid}, session_id: USER_PROFILE")
    print(f" DynamoDB Result → sender_item: {sender_item}")
    if not sender_item:
        raise ValueError("送信者ユーザーが存在しません")

    # ── 2) クライアント証明書 (client_cert) の検証 ────────────────────────
    client_cert_b64 = data.get("client_cert", "")
    if not client_cert_b64:
        raise ValueError("client_cert が不足しています")

    try:
        cert_bytes = base64.b64decode(client_cert_b64)
    except Exception:
        raise ValueError("client_cert は Base64 PEM 形式ではありません")

    # **pyasn1＋Dilithium で証明書検証**
    if not verify_client_certificate(cert_bytes):
        raise ValueError("クライアント証明書の検証に失敗しました")

    # ── 3) クライアントの Dilithium 署名検証 ───────────────────────────
    payload_body       = data.get("payload") or {}
    ntru_cipher_b64    = data.get("ntru_ciphertext", "")
    dilith_sig_b64     = data.get("dilithium_signature", "")
    dilith_pubkey_b64  = data.get("dilithium_public_key", "")

    if not (payload_body and ntru_cipher_b64 and dilith_sig_b64 and dilith_pubkey_b64):
        raise ValueError("payload or ntru_ciphertext or dilithium_signature or dilithium_public_key が不足しています")

    # 3-1) DB に保存済みの Dilithium 公開鍵(Base64) と一致することをチェック
    registered_dilith_pub = sender_item.get("dilithium_public_key", "")
    # print群を追加してチェック
    print(" DB登録済み Dilithium 公開鍵:", registered_dilith_pub)
    print(" 送信データ内 Dilithium 公開鍵:", dilith_pubkey_b64)
    print(" 比較結果 →", registered_dilith_pub == dilith_pubkey_b64)
    if registered_dilith_pub != dilith_pubkey_b64:
        raise ValueError("送信者の Dilithium 公開鍵が一致しません")

    # 3-2) 実際の署名検証
    canonical_bytes = json.dumps(payload_body, sort_keys=True, ensure_ascii=False).encode("utf-8")
    sig_bytes       = base64.b64decode(dilith_sig_b64)
    pubkey_bytes    = base64.b64decode(dilith_pubkey_b64)

    if not verify_message_signature(canonical_bytes, sig_bytes, pubkey_bytes):
        raise ValueError("Dilithium 署名検証に失敗しました")

    # ── 4) NTRU 復号 to shared_secret ──────────────────────────────────
    try:
        cipher_bytes = base64.b64decode(ntru_cipher_b64)
        sk_bytes     = base64.b64decode(sender_item["ntru_secret_key_b64"])
        shared_secret = ntru_decrypt(cipher_bytes, sk_bytes)
    except Exception as e:
        raise ValueError(f"NTRU 復号エラー: {e}")

    # ── 5) 必須フィールドチェック ──────────────────────────────────────────
    required_fields = [
        "receiver_uuid", "amount", "message",
        "subject", "action_level", "dimension",
        "organism_name", "sender_municipality",
        "receiver_municipality", "details",
        "goods_or_money", "location", "proof_of_place"
    ]
    missing = [f for f in required_fields if f not in payload_body or payload_body.get(f, "") == ""]
    if missing:
        raise ValueError(f"必須フィールド不足: {', '.join(missing)}")

    # ── 6) ウォレット残高チェック & 受信者存在チェック ─────────────────────────
    receiver_uuid = payload_body["receiver_uuid"]
    receiver_item = table.get_item(Key={"uuid": receiver_uuid, "session_id": "USER_PROFILE"}).get("Item")
    if not receiver_item:
        raise ValueError("受信者ユーザーが存在しません")

    from login.wallet.wallet_service import get_wallet_by_user  # 後ろで import
    sender_wallet_obj   = get_wallet_by_user(sender_uuid) or type("W", (), {"balance":"1000000"})()
    receiver_wallet_obj = get_wallet_by_user(receiver_uuid) or type("W", (), {"balance":"1000000"})()

    try:
        amount = float(payload_body.get("amount", 0))
    except:
        raise ValueError("amount は数値である必要があります")
    if amount <= 0:
        raise ValueError("amount は正の値である必要があります")
    if float(sender_wallet_obj.balance) < amount:
        raise ValueError("残高不足です (送信者)")

    # ── 7) トランザクション作成 & 固定ハッシュ計算 ──────────────────────────
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"

    from_wallet_encrypted = base64.b64encode(shared_secret).decode("utf-8")
    to_wallet_encrypted   = base64.b64encode(shared_secret).decode("utf-8")

    tx = {
        "transaction_id":        str(uuid.uuid4()),
        "transaction_hash":      "-",  # 後で計算
        "timestamp":             timestamp,
        "sender":                sender_item["username"],
        "receiver":              receiver_item["username"],
        "amount":                amount,
        "subject":               payload_body.get("subject", ""),
        "action_level":          payload_body.get("action_level", ""),
        "dimension":             payload_body.get("dimension", ""),
        "organism_name":         payload_body.get("organism_name", ""),
        "sender_municipality":   payload_body.get("sender_municipality", ""),
        "receiver_municipality": payload_body.get("receiver_municipality", ""),
        "details":               payload_body.get("details", ""),
        "goods_or_money":        payload_body.get("goods_or_money", ""),
        "location":              payload_body.get("location", ""),
        "proof_of_place":        payload_body.get("proof_of_place", ""),
        "from_wallet":           from_wallet_encrypted,
        "to_wallet":             to_wallet_encrypted,
        "encrypted_message":     payload_body.get("message", ""),
        "dilithium_signature":   dilith_sig_b64,
        "status":                "pending"
    }

    IMMUTABLE_FIELDS = [
        "sender", "receiver", "from_wallet", "to_wallet", "amount",
        "transaction_id", "subject", "action_level", "dimension",
        "organism_name", "sender_municipality", "receiver_municipality",
        "details", "goods_or_money", "location", "proof_of_place",
        "encrypted_message", "dilithium_signature"
    ]
    immutable_data = {k: tx[k] for k in IMMUTABLE_FIELDS if k in tx}
    fixed_hash = hashlib.sha256(
        json.dumps(immutable_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    tx["transaction_hash"] = fixed_hash

    # ── 8) CityDAGHandler へキューイング（非同期）───────────────────────
    cont_parts = tx["sender_municipality"].split("/")
    continent = cont_parts[0] if cont_parts and cont_parts[0] else "Default"
    cfg = get_region_config(continent)
    try:
        handler = CityDAGHandler(batch_interval=1, dag_url=cfg["dag_url"])
    except Exception:
        logger.warning("CityDAGHandler の初期化に失敗。ダミー実装を使用します。")
        handler = CityDAGHandler(batch_interval=1)

    # await が必要だが、ダミーならすぐに返る想定
    dag_id, dag_hash = await handler.add_transaction(
        tx["sender"], tx["receiver"], float(tx["amount"]), tx_type="send"
    )
    tx["transaction_id"] = dag_id
    tx["status"] = "send_complete"

    # ── 9) DynamoDB 書き込みを非同期で実行（バックグラウンド）──────────────
    async def async_write_dynamo(item: dict):
        try:
            awsb = boto3.resource("dynamodb", region_name=AWS_REGION)
            tbl = awsb.Table(USERS_TABLE)
            tbl.put_item(Item=item)
        except Exception:
            logger.exception("DynamoDB 書き込みに失敗しました")

    dynamo_record = {
        "uuid":           str(uuid.uuid4()),
        "session_id":     "TX_HISTORY",
        "transaction_id": tx["transaction_id"],
        "sender_uuid":    sender_uuid,
        "receiver_uuid":  receiver_uuid,
        "amount":         str(amount),
        "timestamp":      timestamp,
        "status":         tx["status"]
    }
    asyncio.create_task(async_write_dynamo(dynamo_record))

    # ── 10) 最終レスポンスを返却 ─────────────────────────────────────────────
    return tx
