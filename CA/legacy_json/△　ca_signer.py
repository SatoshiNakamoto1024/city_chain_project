# CA/ca_signer.py

import sys
import os
from datetime import datetime
import json

sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\ntru-py"))
from ntru_encryption import NtruEncryption

ntru = NtruEncryption()

def encrypt_data(pubkey):
    return ntru.encrypt(pubkey)

def decrypt_data(cipher, seckey):
    return ntru.decrypt(cipher, seckey)

def load_ca_private_key():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    key_path = os.path.join(base_dir, "CA", "keys", "ca_private.json")
    with open(key_path, "r") as f:
        key_data = json.load(f)
    return bytes.fromhex(key_data["private_key"])

def serialize_cert_data(data):
    def convert(v):
        if isinstance(v, bytes):
            return v.hex()
        if isinstance(v, dict):
            return {k: convert(val) for k, val in v.items()}
        if isinstance(v, list):
            return [convert(val) for val in v]
        return v
    return convert(data)

def sign_certificate(cert_data: dict) -> dict:
    # ✅ シリアライズ
    cert_data_serialized = serialize_cert_data(cert_data)
    cert_str = json.dumps(cert_data_serialized, sort_keys=True)

    # ✅ NTRUで署名（模擬） ※実際には署名ではない
    ca_priv = load_ca_private_key()
    signature, _ = encrypt_data(ca_priv)  # 擬似的に "署名" のように暗号化

    # ✅ 署名情報を付加
    cert_data["signature"] = signature.hex() if isinstance(signature, bytes) else signature
    cert_data["signed_at"] = datetime.utcnow().isoformat()

    return cert_data  # 署名付きの元データを返す
