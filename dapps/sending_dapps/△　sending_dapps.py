# File: dapps/sending_dapps/sending_dapps.py
"""
sending_dapps.py  — Flask Blueprint 本体

- GET  /send/                         → 送信用フォームを返す
- GET  /send/api/users                → DynamoDB から登録ユーザー一覧を返す（テスト時はダミー5件）
- POST /send/api/send_transaction     → トランザクション生成＋DAG登録（本番実装用）
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

# プロジェクトルートまでのパスを通しておく
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from flask import Blueprint, render_template, request, jsonify
import boto3
from boto3.dynamodb.conditions import Attr

# DynamoDB の設定値
from login.login_app.config import AWS_REGION, USERS_TABLE
# ウォレット取得用
from login.wallet.wallet_service import get_wallet_by_user
# JWT 検証用
from login.auth_py.jwt_manager import verify_jwt

# 本番実装として、Python → Rust/C 実装の NTRU／Dilithium ラッパーを呼び出す
# 「ntrust_native_py」は ntru-py 側でビルド済みの PyO3 ラッパーモジュール
# 「dilithium5」は dilithium-py 側でビルド済みの PyO3 ラッパーモジュール
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\ntru-py"))
try:
    import ntrust_native_py       # NTRU KEM: generate_keypair, encrypt, decrypt
    from ntrust_native_py import generate_keypair as ntru_generate, encrypt as ntru_encrypt, decrypt as ntru_decrypt
except ImportError:
    raise ImportError("ntru-py (ntrust_native_py) が import できません。ビルドを確認してください。")

try:
    import dilithium5             # Dilithium‐5: generate_keypair, sign, verify
    from dilithium5 import generate_keypair as dilithium_generate, sign as dilithium_sign, verify as dilithium_verify
except ImportError:
    raise ImportError("dilithium-py (dilithium5) が import できません。ビルドを確認してください。")

# CA 証明書検証には cryptography パッケージを利用
from cryptography import x509
from cryptography.hazmat.backends import default_backend

# 大陸別 DAG サーバー設定を取得
from dapps.sending_dapps.region_registry import get_region_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

send_bp = Blueprint("send_bp", __name__, template_folder="templates")


# ── CityDAGHandler のインポートをスタブ可能にする ─────────────────────
try:
    # 本番向け CityDAGHandler がインストールされていればこちらが使われる
    from network.sending_DAG.python_sending.city_level.city_dag_handler import CityDAGHandler
except ImportError:
    # テスト時や開発環境で「city_dag_storage」がない場合はダミークラスを定義する
    logger.warning("CityDAGHandler がインポートできなかったため、ダミー実装を使用します。")

    class CityDAGHandler:
        def __init__(self, *args, **kwargs):
            # 引数は無視するダミーコンストラクタ
            pass

        async def add_transaction(self, sender, receiver, amount, tx_type="send"):
            """
            ダミー実装: 実際には DAG には投げず、
            固定の (dag_id, dag_hash) を返す
            """
            dummy_id = "dummy_tx_id_" + uuid.uuid4().hex[:8]
            dummy_hash = "dummy_hash_" + uuid.uuid4().hex[:16]
            return (dummy_id, dummy_hash)
# ────────────────────────────────────────────────────────────────────────


# ── CA 公開鍵をロードして返すユーティリティ ────────────────────────────
def load_ca_public_key(ca_cert_path: str = None):
    """
    ca_cert_path: CA ルート証明書のパス（PEM）。
                  省略時は 'certs/ca_cert.pem' を使う。
    """
    if ca_cert_path is None:
        # プロジェクトルート直下の certs ディレクトリに置かれている想定
        ca_cert_path = os.getenv("CA_CERT_PATH", "D:\\city_chain_project\\CA\\certs\\ca_root_20250503T080950Z.pem")

    if not os.path.isfile(ca_cert_path):
        raise FileNotFoundError(f"CA 証明書が見つかりません: {ca_cert_path}")

    with open(ca_cert_path, "rb") as f:
        cert_data = f.read()
    ca_cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    return ca_cert.public_key()


def verify_client_certificate(cert_pem_bytes: bytes, ca_public_key) -> bool:
    """
    クライアントが送ってきた client_cert.pem バイト列を
    CA の公開鍵で検証して正当なら True、そうでなければ False を返す。
    """
    try:
        cert = x509.load_pem_x509_certificate(cert_pem_bytes, default_backend())
        # 証明書署名を検証
        ca_public_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            cert.signature_hash_algorithm,
        )
        return True
    except Exception as e:
        logger.error(f"[証明書検証エラー] {e}")
        return False


@send_bp.route("/", methods=["GET"])
def send_form():
    """
    ブラウザから /send/ を開いたときに send_screen.html を返す。
    クエリパラメータで wallet, balance を受け取れる。
    """
    wallet = request.args.get("wallet", "N/A")
    balance = request.args.get("balance", "0.00")
    return render_template("send_screen.html",
                           wallet_address=wallet,
                           balance=balance)


@send_bp.route("/api/users", methods=["GET"])
def api_list_users():
    """
    登録済みユーザー一覧を返却します。
    - ?region=Asia の場合：テスト用にダミー5件を返す（ナカモトサトシ含む）
    - ?region=Europe の場合：テスト用にダミー5件を返す（アンナ含む）
    - ?municipality=XXX などが指定されていれば DynamoDB から該当ユーザーを取得
    """
    region = request.args.get("region")
    municipality = request.args.get("municipality")

    # ----- テスト用ダミー5件返却ルート（Asia） -----
    if region == "Asia":
        dummy_users = [
            # テスト用必須ユーザー：ナカモトサトシ（Asia/JP/18/Kanazawa）
            {
                "uuid":          "uuid_kanazawa_01",
                "username":      "ナカモトサトシ_01",
                "municipality":  "Asia/JP/18/Kanazawa",
                "region":        "Asia"
            },
            # 残り4件はプレースホルダー
            {
                "uuid":          "dummy_uuid_a1",
                "username":      "dummy_user_a1",
                "municipality":  "Asia/JP/Tokyo/Shinjuku",
                "region":        "Asia"
            },
            {
                "uuid":          "dummy_uuid_a2",
                "username":      "dummy_user_a2",
                "municipality":  "Asia/JP/Osaka/Kita",
                "region":        "Asia"
            },
            {
                "uuid":          "dummy_uuid_a3",
                "username":      "dummy_user_a3",
                "municipality":  "Asia/CN/Beijing/Haidian",
                "region":        "Asia"
            },
            {
                "uuid":          "dummy_uuid_a4",
                "username":      "dummy_user_a4",
                "municipality":  "Asia/IN/KA/Bangalore",
                "region":        "Asia"
            },
        ]
        return jsonify(dummy_users), 200

    # ----- テスト用ダミー5件返却ルート（Europe） -----
    if region == "Europe":
        dummy_users = [
            # テスト用必須ユーザー：アンナ（Europe/IE/SO/Sligo）
            {
                "uuid":          "uuid_sligo_01",
                "username":      "アンナ_01",
                "municipality":  "Europe/IE/SO/Sligo",
                "region":        "Europe"
            },
            # 残り4件はプレースホルダー
            {
                "uuid":          "dummy_uuid_e1",
                "username":      "dummy_user_e1",
                "municipality":  "Europe/DE/BY/Munich",
                "region":        "Europe"
            },
            {
                "uuid":          "dummy_uuid_e2",
                "username":      "dummy_user_e2",
                "municipality":  "Europe/FR/IDF/Paris",
                "region":        "Europe"
            },
            {
                "uuid":          "dummy_uuid_e3",
                "username":      "dummy_user_e3",
                "municipality":  "Europe/GB/LND/London",
                "region":        "Europe"
            },
            {
                "uuid":          "dummy_uuid_e4",
                "username":      "dummy_user_e4",
                "municipality":  "Europe/IT/LA/Rome",
                "region":        "Europe"
            },
        ]
        return jsonify(dummy_users), 200

    # ---------------------------------------
    # それ以外の場合は DynamoDB から検索する（実運用時）
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(USERS_TABLE)

        if municipality:
            # 市町村でフィルタ: sender_municipality が合致するユーザーを返す
            resp = table.scan(
                FilterExpression=Attr("sender_municipality").eq(municipality)
            )
        elif region:
            # 大陸でフィルタ: region フィールドを使って検索
            resp = table.scan(
                FilterExpression=Attr("region").eq(region)
            )
        else:
            # フィルタなし
            resp = table.scan()

        items = resp.get("Items", []) or []
        users = []
        for u in items:
            # uuid, username, sender_municipality が揃っている場合のみ追加
            if "uuid" in u and "username" in u:
                users.append({
                    "uuid":          u["uuid"],
                    "username":      u["username"],
                    "municipality":  u.get("sender_municipality", "")
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
      "client_cert":           "<Base64 エンコードされた PEM 形式 client_cert.pem>",
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
     2) クライアント証明書 (client_cert) の検証
     3) クライアントが送ってきた Dilithium 署名を検証
     4) クライアントが送ってきた NTRU 暗号文を復号して「共通鍵」を取得
     5) 必須フィールドチェック
     6) 送信者ウォレット残高チェック & 受信者ウォレット存在チェック
     7) 固定ハッシュ計算 (Immutable Fields) → tx["transaction_hash"] に格納
     8) CityDAGHandler へキューイング (非同期)
     9) 200 OK で即時返却 (DynamoDB 書き込みはバックグラウンド)
    """

    # ── １) JWT デコード & 送信者確認 ───────────────────────────────────
    payload = verify_jwt(jwt_token)
    sender_uuid = payload.get("user_uuid") or payload.get("uuid")
    if not sender_uuid:
        raise ValueError("JWT に user_uuid が含まれていません")

    # DynamoDB から送信者基本情報取得を試みる（鍵などを取得するため）
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(USERS_TABLE)

    # “USER_PROFILE” キーで格納してあると仮定
    sender_item = table.get_item(
        Key={"uuid": sender_uuid, "session_id": "USER_PROFILE"}
    ).get("Item")
    if not sender_item:
        raise ValueError("送信者ユーザーが存在しません")

    # ── ２) クライアント証明書 (client_cert) の検証 ────────────────────────
    client_cert_b64 = data.get("client_cert", "")
    if not client_cert_b64:
        raise ValueError("client_cert が指定されていません")

    # Base64 をデコードしてバイト列に
    try:
        cert_bytes = base64.b64decode(client_cert_b64)
    except Exception as e:
        raise ValueError(f"client_cert の Base64 デコードに失敗: {e}")

    # CA の公開鍵をロード
    ca_pubkey = load_ca_public_key()

    # 証明書検証
    if not verify_client_certificate(cert_bytes, ca_pubkey):
        raise ValueError("クライアント証明書の検証に失敗しました")

    # ── ３) クライアントの Dilithium 署名検証 ───────────────────────────
    # クライアントが JSON body で送ってきたフィールドを展開
    payload_body = data.get("payload") or {}
    ntru_cipher_b64       = data.get("ntru_ciphertext", "")
    dilith_sig_b64        = data.get("dilithium_signature", "")
    dilith_pubkey_b64     = data.get("dilithium_public_key", "")

    if not (payload_body and ntru_cipher_b64 and dilith_sig_b64 and dilith_pubkey_b64):
        raise ValueError("payload or ntru_ciphertext or dilithium_signature or dilithium_public_key が不足しています")

    # 3-1) クライアント送信の “Dilithium 公開鍵” と、DB にある “登録時の公開鍵” が一致することをチェック
    #     ※ 登録時に DynamoDB に “dilithium_public_key” を Base64 文字列として保存してある前提
    registered_dilithium_pub_b64 = sender_item.get("dilithium_public_key", "")
    if registered_dilithium_pub_b64 != dilith_pubkey_b64:
        raise ValueError("送信者の Dilithium 公開鍵が一致しません")

    # 3-2) Dilithium 署名検証
    canonical_bytes = json.dumps(payload_body, sort_keys=True, ensure_ascii=False).encode("utf-8")
    signed_bytes    = base64.b64decode(dilith_sig_b64)
    pubkey_bytes    = base64.b64decode(dilith_pubkey_b64)
    try:
        valid = dilithium_verify(canonical_bytes, signed_bytes, pubkey_bytes)
    except Exception as e:
        raise ValueError(f"Dilithium 署名検証エラー: {e}")
    if not valid:
        raise ValueError("Dilithium 署名検証に失敗しました")

    # ── ４) クライアント送信の NTRU 暗号文を復号して「共通鍵」を取得 ───────────────
    try:
        cipher_bytes = base64.b64decode(ntru_cipher_b64)
        sk_bytes     = base64.b64decode(sender_item["ntru_secret_key_b64"])  # DB に Base64 文字列で保存してある前提
        shared_secret = ntru_decrypt(cipher_bytes, sk_bytes)
        # 例：AES-GCM で payload_body["ciphertext"] を復号することも可能
        # ここでは “shared_secret” を取得する手順のみ記載
    except Exception as e:
        raise ValueError(f"NTRU 復号エラー: {e}")

    # ── ５) 必須フィールドチェック ─────────────────────────────────────────
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

    # ── ６) 送信者・受信者のウォレット残高チェック ─────────────────────────────
    receiver_uuid = payload_body["receiver_uuid"]

    # 6-1) 受信者情報取得
    receiver_item = table.get_item(
        Key={"uuid": receiver_uuid, "session_id": "USER_PROFILE"}
    ).get("Item")
    if not receiver_item:
        raise ValueError("受信者ユーザーが存在しません")

    # 6-2) 送信者・受信者のウォレット取得
    sender_wallet_obj = get_wallet_by_user(sender_uuid)
    if not sender_wallet_obj:
        # ウォレットデータがない場合、テスト用ダミーを返す（残高十分とみなす）
        class DummyWalletSender:
            wallet_address = "dummy_sender_wallet"
            balance = "1000000"
        sender_wallet_obj = DummyWalletSender()

    receiver_wallet_obj = get_wallet_by_user(receiver_uuid)
    if not receiver_wallet_obj:
        class DummyWalletReceiver:
            wallet_address = "dummy_receiver_wallet"
            balance = "1000000"
        receiver_wallet_obj = DummyWalletReceiver()

    # 金額チェック
    try:
        amount = float(payload_body.get("amount", 0))
    except:
        raise ValueError("amount は数値である必要があります")
    if amount <= 0:
        raise ValueError("amount は正の値である必要があります")
    if float(sender_wallet_obj.balance) < amount:
        raise ValueError("残高不足です (送信者)")

    # ── ７) トランザクション辞書の組立 & 固定ハッシュ計算 ─────────────────────
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"

    # NTRU 暗号化した共通鍵 (shared_secret) を、そのまま from_wallet / to_wallet 部分に
    # もしくは AES 演算した結果を入れることもできるが、ここでは簡便化して直接バイト列を Base64 にして格納する
    from_wallet_encrypted = base64.b64encode(shared_secret).decode("utf-8")
    to_wallet_encrypted   = base64.b64encode(shared_secret).decode("utf-8")

    tx = {
        "transaction_id":        str(uuid.uuid4()),
        "transaction_hash":      "-",  # 後で固定ハッシュを計算して入れ替える
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
        # 識別用に NTRU で暗号化した “shared_secret” を Base64 で保持
        "from_wallet":           from_wallet_encrypted,
        "to_wallet":             to_wallet_encrypted,
        # 暗号化された共通鍵以外に別途暗号化メッセージがあれば追加
        "encrypted_message":     payload_body.get("message", ""),
        # Dilithium 署名そのものも念のために格納 (オプション)
        "dilithium_signature":   dilith_sig_b64,
        "status":                "pending"
    }

    # Immutable (固定) フィールド一覧
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

    # ── ８) CityDAGHandler へキューイング（ダミースタブ実行） ──────────────────
    cont_parts = tx["sender_municipality"].split("/")
    continent = cont_parts[0] if len(cont_parts) > 0 and cont_parts[0] else "Default"
    cfg = get_region_config(continent)
    try:
        handler = CityDAGHandler(batch_interval=1, dag_url=cfg["dag_url"])
    except Exception:
        logger.warning("CityDAGHandler の初期化に失敗。ダミー実装を使用します。")
        handler = CityDAGHandler(batch_interval=1)

    # await が必要だが、ダミーならすぐ返ってくる
    dag_id, dag_hash = await handler.add_transaction(
        tx["sender"], tx["receiver"], float(tx["amount"]), tx_type="send"
    )
    tx["transaction_id"] = dag_id
    # tx["transaction_hash"] = dag_hash  # ← 差し替えない（固定ハッシュを優先する）

    tx["status"] = "send_complete"

    # ── ９) DynamoDB への書き込みを非同期で実行（バックグラウンド）──────
    #    非同期で失敗しても DLQ に送るなどの設計とする
    async def async_write_dynamo(item: dict):
        try:
            awsb = boto3.resource("dynamodb", region_name=AWS_REGION)
            tbl = awsb.Table(USERS_TABLE)
            tbl.put_item(Item=item, ReturnValues=None)
        except Exception:
            logger.exception("DynamoDB 書き込みに失敗しました")

    # ここではあくまで設計例として「送信者のウォレット履歴」を記録する想定で JSON を作成し、
    # async タスクとして DynamoDB に書き込む
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

    # ── 最終的にレスポンスとしてクライアントへ返却 ─────────────────────────
    return tx


# 既存で __all__ が無い場合
__all__ = [
    "send_bp",
    "ntru_generate", "ntru_encrypt", "ntru_decrypt",
    "dilithium_generate", "dilithium_sign", "dilithium_verify",
]