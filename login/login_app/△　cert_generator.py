# login_app/cert_generator.py

import uuid
import hashlib

def generate_client_certificate(user_uuid):
    """
    本来は実際のX.509証明書を生成し、Base64にしたものやFingerprintを返す。
    ここではサンプルとしてフェイクを生成。
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
