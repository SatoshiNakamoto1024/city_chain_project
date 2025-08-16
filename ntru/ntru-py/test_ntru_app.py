import pytest
from ntru_encryption import NtruEncryption

CRYPTO_PUBLICKEYBYTES = 699
CRYPTO_SECRETKEYBYTES = 935
CRYPTO_CIPHERTEXTBYTES = 699
CRYPTO_BYTES = 32


@pytest.fixture
def ntru():
    return NtruEncryption()


def test_keypair_generation(ntru):
    keypair = ntru.generate_keypair()
    public_key = keypair["public_key"]
    secret_key = keypair["secret_key"]
    # `bytes`型に変換されているか確認
    assert isinstance(public_key, bytes), f"Expected bytes, got {type(public_key)}"
    assert isinstance(secret_key, bytes), f"Expected bytes, got {type(secret_key)}"
    # 公開鍵と秘密鍵の長さが正しいか確認
    assert len(public_key) == CRYPTO_PUBLICKEYBYTES, \
        f"Public key length mismatch: {len(public_key)} != {CRYPTO_PUBLICKEYBYTES}"
    assert len(secret_key) == CRYPTO_SECRETKEYBYTES, \
        f"Secret key length mismatch: {len(secret_key)} != {CRYPTO_SECRETKEYBYTES}"


def test_encryption_decryption(ntru):
    keypair = ntru.generate_keypair()
    public_key = keypair["public_key"]
    secret_key = keypair["secret_key"]

    # 暗号化テスト
    cipher_text, shared_secret = ntru.encrypt(public_key)
    assert isinstance(cipher_text, bytes), "Cipher text should be bytes"
    assert len(cipher_text) == CRYPTO_CIPHERTEXTBYTES, \
        f"Cipher text length mismatch: {len(cipher_text)} != {CRYPTO_CIPHERTEXTBYTES}"

    # 復号化テスト
    decrypted_shared_secret = ntru.decrypt(cipher_text, secret_key)
    assert isinstance(decrypted_shared_secret, bytes), "Shared secret should be bytes"

    # 共有秘密鍵の一致を確認
    assert shared_secret == decrypted_shared_secret, \
        "Shared secrets do not match"
