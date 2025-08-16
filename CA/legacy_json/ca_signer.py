import sys
import os
import json
from datetime import datetime

# Dilithiumのモジュールをインポート
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\dilithium-py"))
from app_dilithium import sign_message, verify_message

# CA秘密鍵・公開鍵のパス
CA_KEY_PATH = "CA/keys/ca_private.json"

def load_ca_keys():
    """
    CAの秘密鍵と公開鍵をロード
    """
    with open(CA_KEY_PATH, "r") as f:
        key_data = json.load(f)
    ca_private_key = bytes.fromhex(key_data["private_key"])
    ca_public_key = bytes.fromhex(key_data["public_key"])
    return ca_private_key, ca_public_key

def sign_certificate(cert_data: dict) -> dict:
    """
    証明書データにDilithium署名を付与して返す
    """
    ca_private_key, ca_public_key = load_ca_keys()

    # 証明書データをソートして文字列化
    cert_data_serialized = serialize_cert(cert_data)
    cert_str = json.dumps(cert_data_serialized, sort_keys=True, separators=(",", ":")).encode("utf-8")

    # Dilithiumで署名を生成
    signed_message = sign_message(cert_str, ca_private_key)

    # 証明書に署名と署名日時を付加
    cert_data["ca_signature"] = signed_message.hex()
    cert_data["signed_at"] = datetime.now(timezone.utc).isoformat()

    return cert_data

def serialize_cert(data):
    """
    証明書データをシリアライズ可能な形（bytesをhex文字列）に変換
    """
    def convert(obj):
        if isinstance(obj, bytes):
            return obj.hex()
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj

    return convert(data)
