# login_app/cert_generator.py
import uuid
import hashlib

def generate_client_certificate(user_uuid: str) -> dict:
    """
    本来は実際のX.509証明書を生成し、Base64化したものやFingerprintを返す。
    ここではサンプルとしてフェイクを生成し、ダミーの証明書データを返す。

    :param user_uuid: ユーザーUUID
    :return: {
        "serial_number": str,
        "valid_from": str (ISO8601),
        "valid_to": str (ISO8601),
        "fingerprint": str (sha256),
        "cert_base64": str (ダミーのBase64)
    }
    """
    fake_serial = uuid.uuid4().hex
    fake_fp = hashlib.sha256(fake_serial.encode()).hexdigest()
    cert_data = {
        "serial_number": fake_serial,
        "valid_from": "2025-04-04T12:34:00Z",
        "valid_to":   "2026-04-04T12:34:00Z",
        "fingerprint": fake_fp,
        "cert_base64": "BASE64_ENCODED_CERT_" + user_uuid
    }
    return cert_data
