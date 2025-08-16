# app_encrypt.py
from rsa_encrypt import generate_keypair, encrypt_message, decrypt_message
from cryptography.hazmat.primitives import serialization
import base64
from rsa_encrypt import generate_keypair as _generate_keypair

def generate_keypair_interface():
    """
    RSA鍵ペアを生成し、鍵オブジェクトを返すインターフェース
    """
    return _generate_keypair()

def main():
    # 鍵ペアの生成
    private_key, public_key = generate_keypair()

    # 鍵をPEM形式でシリアライズ
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    print("Private Key:")
    print(private_pem.decode('utf-8'))
    print("Public Key:")
    print(public_pem.decode('utf-8'))

    # メッセージの暗号化
    message = "Hello, RSA!"
    print(f"Original message: {message}")
    encrypted_message = encrypt_message(public_key, message)
    encoded_encrypted_message = base64.b64encode(encrypted_message).decode('utf-8')
    print(f"Encrypted message (Base64): {encoded_encrypted_message}")

    # メッセージの復号化
    decoded_encrypted_message = base64.b64decode(encoded_encrypted_message.encode('utf-8'))
    decrypted_message = decrypt_message(private_key, decoded_encrypted_message)
    print(f"Decrypted message: {decrypted_message}")

if __name__ == "__main__":
    main()
