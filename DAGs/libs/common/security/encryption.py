# network/DAGs/common/security/encryption.py
"""
encryption.py
AES-GCM によるフィールド暗号化・復号 + CSFLE 用データキー生成
"""
import os
import uuid
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_field(plaintext: bytes, key: bytes) -> bytes:
    """
    AES-GCM で暗号化 → nonce(12B) + ciphertext
    """
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext, None)
    return nonce + ct


def decrypt_field(ciphertext: bytes, key: bytes) -> bytes:
    """
    AES-GCM で復号 → plaintext
    """
    nonce, ct = ciphertext[:12], ciphertext[12:]
    aes = AESGCM(key)
    return aes.decrypt(nonce, ct, None)


def create_data_key() -> tuple[str, bytes]:
    """
    CSFLE 用のデータキー生成 → (key_id, key_bytes)
    """
    key = AESGCM.generate_key(bit_length=256)
    return str(uuid.uuid4()), key
