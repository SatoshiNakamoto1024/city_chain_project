import pytest
from rsa_sign import generate_keypair, sign_message, verify_signature

@pytest.fixture
def rsa_keys():
    private_key, public_key = generate_keypair()
    return private_key, public_key

def test_sign_and_verify(rsa_keys):
    private_key, public_key = rsa_keys
    message = "Test message for signing"

    # 署名の生成
    signature = sign_message(private_key, message)

    # 署名の検証
    assert verify_signature(public_key, message, signature) == True

def test_invalid_signature(rsa_keys):
    private_key, public_key = rsa_keys
    message = "Test message for signing"
    tampered_message = "Tampered message"

    # 署名の生成
    signature = sign_message(private_key, message)

    # 改ざんされたメッセージでの署名検証
    assert verify_signature(public_key, tampered_message, signature) == False
