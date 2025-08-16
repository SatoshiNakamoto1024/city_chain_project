# ntru_encryption.py

import ntrust_native_py
from typing import Tuple


class NtruEncryption:
    def __init__(self):
        pass

    def generate_keypair(self):
        """
        鍵ペアを生成します。
        """
        # Rust側の関数を呼び出して鍵ペアを生成
        keypair = ntrust_native_py.generate_keypair()
        return {
            "public_key": bytes(keypair.public_key),
            "secret_key": bytes(keypair.secret_key),
        }

    def encrypt(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """
        公開鍵を使用してデータを暗号化します。
        """
        if not isinstance(public_key, bytes):
            raise TypeError(f"public_key must be bytes, but got {type(public_key)}")

        # Rust関数の呼び出し
        cipher_text, shared_secret = ntrust_native_py.encrypt(public_key)
        return cipher_text, shared_secret

    def decrypt(self, cipher_text: bytes, secret_key: bytes) -> bytes:
        """
        暗号文と秘密鍵を使用してデータを復号します。
        """
        if not isinstance(cipher_text, bytes) or not isinstance(secret_key, bytes):
            raise TypeError(
                f"cipher_text and secret_key must be bytes, but got {type(cipher_text)} and {type(secret_key)}"
            )

        # Rust関数の呼び出し
        shared_secret = ntrust_native_py.decrypt(cipher_text, secret_key)
        return shared_secret
