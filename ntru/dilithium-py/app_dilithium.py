# D:\city_chain_project\ntru\dilithium-py\app_dilithium.py
import dilithium5

def create_keypair():
    """
    Rust側の generate_keypair() を呼び出して
    (public_key, secret_key) を返す。
    """
    public_key, secret_key = dilithium5.generate_keypair()
    return public_key, secret_key


def sign_message(message: bytes, secret_key: bytes) -> bytes:
    """
    Rust側の sign() を呼び出し、
    「署名付きメッセージ(SignedMessage)」のバイト列を返す。
    """
    signed_message = dilithium5.sign(message, secret_key)
    return signed_message


def verify_message(message: bytes, signed_message: bytes, public_key: bytes) -> bool:
    """
    Rust側の verify() を呼び出し、
    (message, signed_message, public_key) が正しいなら True、それ以外は False を返す。
    """
    return dilithium5.verify(message, signed_message, public_key)


def create_and_sign_message(message: bytes) -> tuple[bytes, bytes, bytes]:
    """
    1. 鍵ペア生成
    2. メッセージに署名し、署名付きメッセージを生成
    3. (public_key, secret_key, signed_message) をまとめて返す
    """
    public_key, secret_key = create_keypair()
    signed_message = sign_message(message, secret_key)
    return public_key, secret_key, signed_message
