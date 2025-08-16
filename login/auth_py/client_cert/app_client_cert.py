# auth_py/client_cert/app_client_cert.py
"""
クライアント証明書発行・取得 API（PEM 版）
"""

from __future__ import annotations
import os, sys, json, base64, hashlib
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Tuple

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.exceptions import BadRequest
import boto3

# ──────────────────────────────────────────────
# 自前モジュール
# ──────────────────────────────────────────────
PACKAGE_ROOT = Path(__file__).resolve().parent
sys.path += [
    str(PACKAGE_ROOT),                     # …/client_cert/
    str(PACKAGE_ROOT.parent.parent)        # …/auth_py/
]

from client_cert_manager import request_cert, load_cert
from dilithium_verify    import verify_pem
from client_keygen       import generate_client_keys  

# ──────────────────────────────────────────────
# AWS / 保存先
# ──────────────────────────────────────────────
AWS_REGION     = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET      = os.getenv("S3_BUCKET", "my-client-cert-bucket")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "ClientCertificates")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table    = dynamodb.Table(DYNAMODB_TABLE)
s3       = boto3.client("s3", region_name=AWS_REGION)

LOCAL_META_DIR = Path(r"D:\city_chain_project\login\login_data\user_id_metadata")
LOCAL_CERT_DIR = Path(r"D:\city_chain_project\login\login_data\user_client_cert")
LOCAL_META_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_CERT_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# Flask
# ──────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# -----------------------------------------------------------------
# 便利関数（公開用）
# -----------------------------------------------------------------
def generate_client_keys_interface() -> dict[str, bytes]:
    """NTRU+Dilithium 鍵ペアを返す（API 他から呼び出し用）"""
    return generate_client_keys()

# -----------------------------------------------------------------
# 内部ユーティリティ
# -----------------------------------------------------------------
def _fingerprint(der: bytes) -> str:
    return hashlib.sha256(der).hexdigest()

def _pem_to_der(pem: str) -> bytes:
    b64 = b"".join(bytes([l]) for l in pem.encode() if l not in b"\r\n-")
    return base64.b64decode(b64)

# -----------------------------------------------------------------
# /client_cert  POST  ―― 新規発行 or 既存返却
# -----------------------------------------------------------------
@app.route("/client_cert", methods=["POST"])
def client_cert_issue():
    if not request.is_json:
        raise BadRequest("json required")

    j = request.get_json()
    uuid_val = j.get("uuid")
    if not uuid_val:
        raise BadRequest("uuid missing")

    # ---- 既存チェック -------------------------------------------------
    item = table.get_item(Key={"uuid": uuid_val,
                               "session_id": "CLIENT_CERT"}).get("Item")
    if item and not item["revoked"]:
        pem_bytes = load_cert(uuid_val)
        return jsonify({"uuid": uuid_val,
                        "fingerprint": item["fingerprint"],
                        "pem": pem_bytes.decode()})

    # ---- 新規発行 -----------------------------------------------------
    try:
        ntru_pub = base64.b64decode(j["ntru_public_b64"])
        dil_pub  = bytes.fromhex(j["dil_public_hex"])
        print(" Dilithium 公開鍵 →", dil_pub.hex()) 
    except Exception as e:
        raise BadRequest(f"bad key format: {e}")

    # CA から PEM を取得してファイルに保存
    pem_path  = request_cert(uuid_val, ntru_pub, dil_pub)
    pem_bytes = pem_path.read_bytes()

    # cryptography を使った再ロードはカスタムOIDで失敗するのでスキップ
    # try:
    #     from cryptography import x509
    #     from cryptography.hazmat.primitives import serialization
    #     cert2 = x509.load_pem_x509_certificate(pem_bytes)
    #     pem_bytes = cert2.public_bytes(serialization.Encoding.PEM)
    # except Exception:
    #     # 再ロードできない場合は元の pem_bytes のまま
    #     pass

    # DER から fingerprint を直接計算
    fp = _fingerprint(_pem_to_der(pem_bytes.decode()))

    # DynamoDB 登録
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    tbl_item = {
        "uuid":        uuid_val,
        "session_id":  "CLIENT_CERT",
        "fingerprint": fp,
        "issued_at":   now_iso,
        "revoked":     False,
        "revoked_at":  None
    }
    table.put_item(Item=tbl_item)

    # ローカル保存
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    LOCAL_META_DIR.joinpath(f"{uuid_val}_{stamp}.json")\
        .write_text(json.dumps(tbl_item, indent=2), encoding="utf-8")
    LOCAL_CERT_DIR.joinpath(f"{uuid_val}_{stamp}.pem").write_bytes(pem_bytes)

    return jsonify({"uuid": uuid_val,
                    "fingerprint": fp,
                    "pem": pem_bytes.decode()})

# -----------------------------------------------------------------
# /download_cert_pem  GET
# -----------------------------------------------------------------
@app.route("/download_cert_pem", methods=["GET"])
def download_cert_pem():
    uuid_val = request.args.get("uuid")
    if not uuid_val:
        raise BadRequest("uuid missing")

    try:
        pem_bytes = load_cert(uuid_val)
        return send_file(BytesIO(pem_bytes),
                         download_name=f"{uuid_val}.pem",
                         mimetype="application/x-pem-file",
                         as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "not found"}), 404

# -----------------------------------------------------------------
# /revoke_cert  POST
# -----------------------------------------------------------------
@app.route("/revoke_cert", methods=["POST"])
def revoke_cert():
    j = request.get_json() or {}
    uuid_val = j.get("uuid")
    if not uuid_val:
        raise BadRequest("uuid missing")

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    table.update_item(Key={"uuid": uuid_val, "session_id": "CLIENT_CERT"},
                      UpdateExpression="SET revoked=:r, revoked_at=:t",
                      ExpressionAttributeValues={":r": True, ":t": now_iso})
    return jsonify({"uuid": uuid_val, "revoked": True, "revoked_at": now_iso})

# ────────────────────────────────────────────────
# 追加／再定義　※ファイル末尾付近に置けば OK
# ────────────────────────────────────────────────

def build_client_certificate_interface(uuid_val: str,
                                       ntru_pub: bytes,
                                       dil_pub: bytes) -> Tuple[str, str]:
    """
    旧 JSON 証明書ビルダーの “名前” だけ残し、
    内部では CA へ問い合わせて PEM を取ってくる。
      戻り値: (pem_str, fingerprint)
    """
    pem_path  = request_cert(uuid_val, ntru_pub, dil_pub)
    pem_bytes = pem_path.read_bytes()
    fp = hashlib.sha256(_pem_to_der(pem_bytes.decode())).hexdigest()
    return pem_bytes.decode(), fp

# -----------------------------------------------------------------
if __name__ == "__main__":
    app.run(port=6001, debug=True)
