# CA/app_ca.py
"""
外部から **唯一** 直接 import してもらうモジュール。
ここには “インターフェース関数” だけを置き、重い処理は ca_core.py に委譲する。
"""

from .ca_core import generate_and_sign_certificate  # re-export 用

def generate_certificate_interface(
        user_uuid: str,
        ntru_public_key: bytes,
        dilithium_public_key_hex: str,
        validity_days: int = 365
):
    """
    registration.py などから呼ばれる唯一の窓口。
    戻り値: (cert_bytes, fingerprint_hex)
    """
    return generate_and_sign_certificate(
        user_uuid, ntru_public_key, dilithium_public_key_hex, validity_days
    )
