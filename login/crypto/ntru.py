# crypto/ntru.py
def encrypt(message: str, public_key: str) -> str:
    # ダミー実装: 文字列を逆順にして "encrypted" と付加する
    return message[::-1] + "_ntru"

def decrypt(encrypted_message: str, private_key: str) -> str:
    # ダミー実装: "_ntru" を除去して逆順に戻す
    if encrypted_message.endswith("_ntru"):
        core = encrypted_message[:-5]
        return core[::-1]
    else:
        raise ValueError("Invalid encrypted message")
