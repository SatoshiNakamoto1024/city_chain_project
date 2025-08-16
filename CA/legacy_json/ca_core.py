# CA/ca_core.py
import os, sys, json, uuid, base64
from datetime import datetime, timedelta, timezone
from typing import Tuple
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from .ca_signer import sign_certificate, load_ca_private_key   # すでに実装済みのモジュール

sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\ntru-py"))
from ntru_encryption import NtruEncryption                     # NTRU 暗号

sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\dilithium-py"))
from dilithium_app import sign_message                         # Dilithium 署名

# ==========================================================
# 共通ヘルパ
# ==========================================================
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()

# ==========================================================
# 証明書生成
# ==========================================================
def generate_cert_payload(
        user_uuid: str,
        ntru_public_key: bytes,
        dilithium_public_key_hex: str,
        validity_days: int = 365
) -> dict:
    """
    ユーザー情報と公開鍵を受け取り、署名前の「証明書ペイロード」を組み立てる。
    """
    return {
        "uuid":           user_uuid,
        "algorithm":      "NTRU+Dilithium",
        "ntru_public":    base64.b64encode(ntru_public_key).decode(),
        "dilithium_public": dilithium_public_key_hex.lower(),
        "issuer":         "Example CA",
        "serial_number":  uuid.uuid4().hex,
        "valid_from":     _to_iso(_now_utc()),
        "valid_to":       _to_iso(_now_utc() + timedelta(days=validity_days)),
        "revoked":        False,
    }

def generate_and_sign_certificate(
        user_uuid: str,
        ntru_public_key: bytes,
        dilithium_public_key_hex: str,
        validity_days: int = 365
) -> Tuple[bytes, str]:
    """
    1. ペイロード生成 → 2. CA 署名 → 3. JSON + Base64 エンコードを返す
       戻り値: (cert_bytes, fingerprint_hex)
    """
    # ① ペイロード
    cert_dict = generate_cert_payload(
        user_uuid, ntru_public_key, dilithium_public_key_hex, validity_days
    )

    # ② CA 署名（NTRU で暗号化したバイト列を signature に格納）
    cert_signed_dict = sign_certificate(cert_dict)   # → 'signature' フィールド追加済み

    # ③ バイト列化（UTF-8）/ fingerprint
    cert_json = json.dumps(cert_signed_dict, separators=(",", ":")).encode()
    fingerprint_hex = uuid.uuid5(uuid.NAMESPACE_OID, cert_json.hex()).hex

    return cert_json, fingerprint_hex
