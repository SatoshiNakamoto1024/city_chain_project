# registration/registration.py
import sys, os, io
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import binascii
import traceback
import uuid
import logging
import base64
import json
import hashlib 
import time
from datetime import datetime, timezone
import boto3
from boto3.dynamodb.conditions import Key as DynamoKey
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for

from auth_py.app_auth import log_to_cloudwatch_interface
from auth_py.auth_with_cert import cert_pem_to_fingerprint
from auth_py.fingerprint import calc_fp_from_pem
from auth_py.password_manager import hash_password as _hash_pw_common_
from registration.pairing_token import create_pairing_token
from registration.pairing_token import consume_pairing_token

##########################
# AWS & Config
##########################
from registration.config import AWS_REGION, S3_BUCKET, DYNAMODB_TABLE, DEVICES_TABLE

s3 = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(DYNAMODB_TABLE)
devices_table = dynamodb.Table(DEVICES_TABLE)

##########################
# Auth & CA Integration
##########################
#   - user_manager.* や auth_py.* などを使ってユーザー情報保存やパスワードハッシュを行う
# ここでは auth_py.app_auth.* を利用（パスワードハッシュ、ユーザー保存など）
from auth_py.app_auth import (
    save_user_to_dynamodb_interface as _save_user_,
    hash_password_interface       as _hash_pw_,
    generate_salt_interface       as _gen_salt_
)

##########################
# Client Cert Integration
##########################
from auth_py.client_cert.app_client_cert import (
    generate_client_keys_interface,
    build_client_certificate_interface
)
from auth_py.fingerprint import normalize_fp

##########################
# Dillithium integration
##########################
# Rustバインディングされたdilithium_app.pyを使う
# 例: create_keypair() -> (public_key: bytes, secret_key: bytes)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ntru", "dilithium-py")))
from app_dilithium import create_keypair

# 秘密鍵のPEMをBase64でエンコードしてレスポンスに追加する
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ntru", "rsa-encrypt-py")))
from app_encrypt import generate_keypair_interface
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def register_user(registration_data: dict) -> dict:
    """
    ユーザー登録処理:
      - 必須項目チェック
      - 2台目端末登録の場合 -> 'qr_code' フィールドの有無で判断
      - 新規ユーザー登録の場合 -> パスワードハッシュ, CA発行, Dillithium鍵生成, DynamoDB/S3保存
      - clientにDillithium秘密鍵を返す
    """

    # 2台目端末登録かどうかチェック
    qr_code = registration_data.get("qr_code")
    logger.info(f"受け取ったqr_code: {qr_code}")
    if qr_code:
        # 安全にusername / password を検証
        username = registration_data.get("username")
        password = registration_data.get("password")
        if not username or not password:
            raise Exception("2台目端末登録には username と password が必要です")

        # 分岐して2台目登録
        return register_second_device_via_qr(qr_code, registration_data)

    # 新規ユーザー登録
    username = registration_data.get("username")
    email = registration_data.get("email")
    password = registration_data.get("password")
    if not username or not email or not password:
        raise Exception("username, email, and password are required")

    # UUID生成、ソルト・ハッシュ計算
    user_uuid = str(uuid.uuid4())
    salt_bytes = _gen_salt_()     
    if isinstance(salt_bytes, str):
        salt_hex = salt_bytes  # すでにhex文字列ならそのまま
    else:
        salt_hex = salt_bytes.hex()  # bytesならhexに変換             # ← 16進文字列に変換
    password_hash = _hash_pw_common_(password, salt_bytes)   # ← ここを統一

    # CA発行のクライアント証明書
    # NTRU + Dilithium鍵ペア生成 & クライアント証明書作成
    keys = generate_client_keys_interface()          # NTRU & Dilithium 鍵ペア
    pem_in = registration_data.get("client_cert_pem")
    fp_in  = registration_data.get("client_cert_fp")

    if pem_in:
        # 既に PEM が送られて来た場合（第一引数を最優先）
        pem_bytes = pem_in.encode() if isinstance(pem_in, str) else pem_in
    else:
        # CA サーバーから証明書をもらう（起動直後だと繋がらないことがあるのでリトライ）
        from time import sleep
        MAX_TRIES = 6
        for attempt in range(MAX_TRIES):
            try:
                pem_bytes, _ = build_client_certificate_interface(
                    user_uuid,
                    keys["ntru_public"],
                    keys["dilithium_public"],
                )
                break
            except Exception as e:
                # 最終試行なら例外を吐く
                if attempt == MAX_TRIES - 1:
                    raise
                logger.warning("CA 応答なし、リトライ中… (%d/%d) : %s", attempt+1, MAX_TRIES, e)
                sleep(0.3)
        
    # PEM を str に統一（改行コードもここで整う）
    pem_str = pem_bytes.decode() if isinstance(pem_bytes, (bytes, bytearray)) else pem_bytes

    # ─────────────────────────────────────────
    #  指紋は「PEM そのもの」を SHA‑256 → normalize_fp
    # ─────────────────────────────────────────
    cert_fp_norm = calc_fp_from_pem(pem_str)

    # bytes が必要な後段用に戻す
    pem_bytes = pem_str.encode()

    # ユーザーが fingerprint を明示した場合はそれを優先する
    if fp_in:
        cert_fp_norm = normalize_fp(fp_in)

    # 後段で共通して扱えるよう dict 化
    pem_str = pem_bytes if isinstance(pem_bytes, str) else pem_bytes.decode()
    
    cert_dict = {
        "pem":         pem_str,
        "fingerprint": cert_fp_norm,
    }

    cert_dict["client_cert"] = base64.b64encode(
        json.dumps(cert_dict, ensure_ascii=False).encode()
    ).decode()
    print("REG‑SAVE", cert_fp_norm[:16], flush=True)
    
    # CloudWatchログ送信
    log_to_cloudwatch_interface("CERT_ISSUED", {
        "uuid": user_uuid,
        "fingerprint": cert_fp_norm,
        "who": "user",
        "from": "register_user",
    })

    # cert_data["public_key"] が list[int] で来る場合があるので必ず文字列化
    pub_raw = keys["dilithium_public"]          # bytes
    public_key_b64 = base64.b64encode(pub_raw).decode()

    if isinstance(pub_raw, list):                  # list[int] → bytes → b64str
        public_key_b64 = base64.b64encode(bytes(pub_raw)).decode("utf-8")
    elif isinstance(pub_raw, (bytes, bytearray)):  # bytes   → b64str
        public_key_b64 = base64.b64encode(pub_raw).decode("utf-8")
    elif isinstance(pub_raw, str):                 # 既に文字列 (hex 等) はそのまま
        public_key_b64 = pub_raw
    else:                                          # None など
        public_key_b64 = ""
    register_time = datetime.now(timezone.utc).isoformat()

    # Dillithium鍵ペア生成 (Rustバインディング)
    if "public_key" in registration_data and registration_data["public_key"]:
        # クライアントから公開鍵と秘密鍵が送られてきた場合
        dilithium_public_key = registration_data["public_key"]
        dilithium_secret_key = registration_data.get("secret_key")

        if not dilithium_secret_key:
            raise Exception("Dillithium秘密鍵がNoneになっています")

        # 公開鍵を bytes に変換
        if isinstance(dilithium_public_key, list):
            dilithium_public_key_bytes = bytes(dilithium_public_key)
        elif isinstance(dilithium_public_key, (bytes, bytearray)):
            dilithium_public_key_bytes = dilithium_public_key
        else:
            raise Exception("公開鍵の形式が不正です")

        # 秘密鍵も bytes に変換
        if isinstance(dilithium_secret_key, list):
            dilithium_secret_key_bytes = bytes(dilithium_secret_key)
        elif isinstance(dilithium_secret_key, (bytes, bytearray)):
            dilithium_secret_key_bytes = dilithium_secret_key
        else:
            raise Exception("秘密鍵の形式が不正です")

    else:
        # サーバーで新規生成
        dilithium_public_key_bytes, dilithium_secret_key_bytes = create_keypair()

    # 16進文字列へ変換（保存用）
    if isinstance(dilithium_public_key_bytes, list):
        dilithium_public_key_bytes = bytes(dilithium_public_key_bytes)
    if isinstance(dilithium_secret_key_bytes, list):
        dilithium_secret_key_bytes = bytes(dilithium_secret_key_bytes)
    
    dilithium_pub_hex = dilithium_public_key_bytes.hex()
    dilithium_sec_hex = dilithium_secret_key_bytes.hex()
    # --- 鍵を表示させて検証 ---------------------------------
    logger.info("DILITHIUM secret_key: %s", dilithium_secret_key_bytes.hex())
    logger.info("NTRU private_key: %s", keys["ntru_private"].hex())

    # ★1 ここで hex 文字列を作る -------------
    ntru_priv_hex = keys["ntru_private"].hex()
    dil_priv_hex  = dilithium_secret_key_bytes.hex()

    # RSA鍵ペア生成（この行を追加！）
    rsa_private_key, rsa_public_key = generate_keypair_interface()
    rsa_private_pem = rsa_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    rsa_private_key_b64 = base64.b64encode(rsa_private_pem).decode("utf-8")

    # user_record を構築
    user_record = {
        "uuid":                     user_uuid,
        "session_id":               "REGISTRATION",
        "username":                 username,
        "email":                    email,
        "password_hash":            password_hash,
        "salt":                     salt_hex,  # 16進文字列で保存
        "certificate":              cert_dict,      # ← 名前を合わせる
        "public_key":               public_key_b64,  # ← 文字列確定
        "dilithium_public_key":     dilithium_pub_hex,
        "client_cert_fingerprint":  cert_fp_norm,
        "created_at":               register_time,
        "ntru_private_key":         ntru_priv_hex,
        "dilithium_private_key":    dil_priv_hex,
        "rsa_private_key":          rsa_private_key_b64,
    }

    # ① UsersTable へ保存 (_save_user_ で済)
    reg_item = user_record.copy()
    reg_item["session_id"] = "REGISTRATION"
    users_table.put_item(Item=reg_item)

    #  USER_PROFILE 行 ----------------------------------------
    profile_item = user_record.copy()
    profile_item["session_id"] = "USER_PROFILE"
    users_table.put_item(Item=profile_item)
    resp = users_table.query(
        KeyConditionExpression=DynamoKey("uuid").eq(user_uuid),
        ConsistentRead=True,
    )
    logger.info("DEBUG scan after register -> %s", resp.get("Items"))

    # ② **DevicesTable に“親機”を登録**
    devices_table = dynamodb.Table(DEVICES_TABLE)
    try:
        devices_table.put_item(Item={
            "uuid":          user_uuid,
            "device_id":     "primary",               # 好きな ID で OK
            "device_name":   registration_data.get("device_name", "PrimaryDevice"),
            "fingerprint":   cert_fp_norm,
            "registered_at": register_time
        })
    except Exception as e:
        logger.error("DevicesTable 登録エラー: %s", e)
        raise

    # S3保存
    timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    s3_filename = f"user_register/{user_uuid}_{timestamp_str}.json"
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_filename,
            Body=json.dumps(user_record, ensure_ascii=False, indent=4),
            ContentType="application/json"
        )
    except Exception as e:
        logger.error("S3保存エラー: %s", e)
        raise Exception("S3 error: " + str(e))

    # ローカル保存
    LOCAL_SAVE_DIR = r"D:\city_chain_project\login\login_data\user_register"
    os.makedirs(LOCAL_SAVE_DIR, exist_ok=True)
    local_filename = os.path.join(LOCAL_SAVE_DIR, f"{user_uuid}_{timestamp_str}.json")
    try:
        with open(local_filename, "w", encoding="utf-8") as f:
            json.dump(user_record, f, ensure_ascii=False, indent=4)
        logger.info("Local saving succeeded: %s", local_filename)
    except Exception as e:
        logger.error("Local saving error: %s", e)
        raise Exception("Local saving error: " + str(e))

    # SNS通知（メールなど）
    try:
        from registration.email_sender import send_registration_notification
        send_registration_notification(username, email, user_uuid)
    except Exception as e:
        logger.error("SNS notification error (non-fatal): %s", e)

    # QRコードに埋め込むデータを base64形式にする
    pairing_token = create_pairing_token(user_uuid)
    qr_payload = {"uuid": user_uuid, "token": pairing_token}
    qr_code_base64 = base64.b64encode(json.dumps(qr_payload).encode()).decode()

    if isinstance(dilithium_secret_key_bytes, list):
        dilithium_secret_key_bytes = bytes(dilithium_secret_key_bytes)
    
    # --- client_cert: PEM と fingerprint を含む JSON を Base64 ---
    cert_json_b64 = base64.b64encode(
        json.dumps(cert_dict, ensure_ascii=False).encode()
    ).decode()
    # 追加: PEM → Base64
    client_cert_pem_b64 = base64.b64encode(pem_bytes).decode()
 
    response = {
        "success":             True,
        "uuid":                user_uuid,
        "certificate":         cert_dict,
        "client_cert":         client_cert_pem_b64,   # ← テストが参照する
        "client_cert_json":    cert_json_b64,         # ← 既存互換用
        "fingerprint":         cert_fp_norm,
        "dilithium_secret_key": dilithium_secret_key_bytes.hex() if dilithium_secret_key_bytes else None,
        "secret_key":          list(dilithium_secret_key_bytes),  # 内部ではdilithium、外部にはsecret_key というバランスを保つ
        "rsa_private_key":     rsa_private_key_b64,
        "ntru_private_key":    ntru_priv_hex, 
        "dilithium_private_key": dil_priv_hex, 
        "qr_code":             qr_code_base64,
        "message":             "User registered successfully. Save your certificate and Dillithium private key securely."
    }
    return response


def fix_base64_padding(s):
    return s + '=' * (-len(s) % 4)


def to_hex(x):
    if x is None:
        return None
    if isinstance(x, str):          # すでに hex 文字列 or Base64
        try:
            bytes.fromhex(x)        # ← hex なら例外なし
            return x.lower()
        except ValueError:
            return x                # Base64 のまま保存
    if isinstance(x, list):
        x = bytes(x)
    return x.hex()


def register_second_device_via_qr(qr_code: str, registration_data: dict) -> dict:
    """
    ワンタイム・トークン方式での 2 台目以降登録
    ① QR(base64) → uuid + token を取得
    ② token を consume（使い切り & 有効期限チェック）
    ③ username / password 検証
    ④  新しいクライアント証明書を発行（端末専用）
    ⑤ DevicesTable へ保存
    """
    # --- デコード & キー取得
    try:
        payload    = json.loads(base64.b64decode(qr_code).decode())
        user_uuid  = payload["uuid"]
        # テスト側は "device_token" キーを返す
        token      = payload.get("token") or payload.get("device_token")
        expires_at = payload.get("expires_at")
    except Exception:
        raise Exception("QR コードが壊れています")

    # --- ペイロード側の有効期限チェック
    if expires_at is not None and expires_at < int(time.time()):
        raise Exception("ペアリングトークン期限切れ")

    # --- DB 側のトークン消費チェック
    if consume_pairing_token(token) != user_uuid:
        raise Exception("ペアリングトークン無効または期限切れ")

    # --- username / password 確認 ----------------------
    username = registration_data.get("username")
    password = registration_data.get("password")
    if not username or not password:
        raise Exception("username / password が必要です")

    resp = users_table.get_item(Key={"uuid": user_uuid, "session_id": "REGISTRATION"})
    user_item = resp.get("Item")
    if not user_item or user_item["username"] != username:
        raise Exception("ユーザが一致しません")

    salt = bytes.fromhex(user_item["salt"])
    if _hash_pw_(password, salt) != user_item["password_hash"]:
        raise Exception("パスワード不一致")

    # ---  新しい端末用クライアント証明書 ----------------
    keys = generate_client_keys_interface()
    pem_bytes, fp_raw = build_client_certificate_interface(
        user_uuid,
        keys["ntru_public"],
        keys["dilithium_public"],
    )
    # ---- finger‑print を 1 台目と同じ方法で計算し直す ----
    if isinstance(pem_bytes, str):
        pem_bytes = pem_bytes.encode()
    fp_norm = normalize_fp(hashlib.sha256(pem_bytes).hexdigest())
    
    # ── ここを追加 ──
    # build_client_certificate_interface が文字列を返す場合があるので、
    # 必ず bytes に変換してから base64 に乗せる
    if isinstance(pem_bytes, str):
        pem_bytes = pem_bytes.encode()

    # DevicesTable へ登録（既に生成済みのものを使う）
    device_id = "dev-" + uuid.uuid4().hex[:6]
    devices_table.put_item(Item={
        "uuid":          user_uuid,
        "device_id":     device_id,
        "device_name":   registration_data.get("device_name", device_id),
        "fingerprint":   fp_norm,
        "registered_at": datetime.now(timezone.utc).isoformat()
    })

    return {
        "success": True,
        "message": "端末を登録しました",
        "uuid":    user_uuid,
        "device_id": device_id,
        "client_cert": base64.b64encode(pem_bytes).decode(),
        "fingerprint": fp_norm
    }

def get_certificate_info(cert_uuid: str) -> dict:
    """
    指定した UUID のクライアント証明書メタデータを返します。
    """
    cert_table = dynamodb.Table("ClientCertificates")  # ← 実際のテーブル名にあわせて修正
    try:
        resp = cert_table.get_item(Key={"uuid": cert_uuid, "session_id": "CLIENT_CERT"})
        item = resp.get("Item")
        if not item:
            raise Exception("Certificate metadata not found")
        return item
    except Exception as e:
        logger.error("Certificate info lookup error: %s", e)
        raise
    
# テスト起動用
if __name__ == "__main__":
    test_data = {
        "username": "sns_test_user",
        "email":    "sns_test@example.com",
        "password": "TestPass123"
    }
    try:
        result = register_user(test_data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error("ユーザー登録で例外発生: %s", str(e))
        traceback.print_exc()
