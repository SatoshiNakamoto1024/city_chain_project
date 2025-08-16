# D:\city_chain_project\ntru\ntru-py\app_ntru.py

from ntru_encryption import NtruEncryption


def main():
    ntru = NtruEncryption()

    # 鍵ペアの生成
    keypair = ntru.generate_keypair()
    public_key = keypair["public_key"]  # bytes型
    secret_key = keypair["secret_key"]  # bytes型
    print("Public Key Type:", type(public_key))
    print("Secret Key Type:", type(secret_key))
    print("Public Key (first 10 bytes):", list(public_key)[:10])  # 簡潔表示
    print("Secret Key (first 10 bytes):", list(secret_key)[:10])

    # データの暗号化
    cipher_text, shared_secret = ntru.encrypt(public_key)
    print("Cipher Text (first 10 bytes):", list(cipher_text)[:10])  # 簡潔表示
    print("Shared Secret (first 10 bytes):", list(shared_secret)[:10])

    # データの復号
    decrypted_shared_secret = ntru.decrypt(cipher_text, secret_key)
    print(
        "Decrypted Shared Secret (first 10 bytes):",
        list(decrypted_shared_secret)[:10],
    )

    # 共有秘密鍵の検証
    if shared_secret == decrypted_shared_secret:
        print("Shared secret validation successful!")
    else:
        print("Shared secret validation failed!")


if __name__ == "__main__":
    main()
