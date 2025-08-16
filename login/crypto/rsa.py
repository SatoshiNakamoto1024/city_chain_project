# crypto/rsa.py
def encrypt(data: str, public_key: str) -> str:
    # ダミー実装: 文字列に "rsa" を付加
    return f"rsa({data})"

def decrypt(encrypted_data: str, private_key: str) -> str:
    # ダミー実装: "rsa(...)" の形式から元の文字列を取り出す
    if encrypted_data.startswith("rsa(") and encrypted_data.endswith(")"):
        return encrypted_data[4:-1]
    else:
        raise ValueError("Invalid RSA encrypted data")
