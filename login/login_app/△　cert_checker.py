# login_app/cert_checker.py
"""
cert_checker.py

UsersTable の証明書メタデータと、クライアントから送られてきた
Base64 証明書(JSON) を突き合わせて検証するユーティリティ。
"""

from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import base64, json, logging, os, hashlib, requests

from login_app.config import (
    CLIENT_CERT_ENDPOINT,   # /client_cert/check_cert?uuid=... と同一サービス
    CERT_BUCKET,            # 失効チェックが不要なら未使用
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def _fingerprint_from_cert_json(cert_json: dict) -> str:
    """証明書 JSON(dict) から fingerprint を取り出す。なければ self-hash を返す。"""
    if "fingerprint" in cert_json:
        return cert_json["fingerprint"]
    # fallback: 証明書 JSON 自体の SHA‑256 を fingerprint とみなす
    digest = hashlib.sha256(json.dumps(cert_json, sort_keys=True).encode()).hexdigest()
    return digest

def verify_certificate(user_item: dict, cert_b64: str) -> None:
    """
    - Base64 の証明書文字列をパース
    - UsersTable に保存してある fingerprint と比較
    - 失効していないか /client_cert/check_cert で確認
    OK なら None を返す。NG は ValueError を送出。
    """
    try:
        cert_bytes = base64.b64decode(cert_b64)
        cert_json  = json.loads(cert_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"client_cert malformed ({e})")

    presented_fp = _fingerprint_from_cert_json(cert_json)
    stored_meta  = user_item.get("certificate", {})
    stored_fp    = stored_meta.get("fingerprint")

    if not stored_fp or presented_fp != stored_fp:
        raise ValueError("certificate fingerprint mismatch")

    # 失効フラグ（ローカルメタデータ）
    if stored_meta.get("revoked"):
        raise ValueError("certificate already revoked")

    # オンライン失効チェック（DynamoDB の最新値を見に行く）
    try:
        res = requests.get(
            CLIENT_CERT_ENDPOINT.replace("/client_cert", "/check_cert"),
            params={"uuid": user_item["uuid"]},
            timeout=3,
        )
        res.raise_for_status()
        meta = res.json()
        if meta.get("revoked"):
            raise ValueError("certificate is revoked (online)")
    except requests.exceptions.RequestException as e:
        logger.warning("revocation check skipped: %s", e)   # ネットワーク障害など

    # OK
    return
