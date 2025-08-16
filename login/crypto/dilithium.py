# crypto/dilithium.py
def sign(message: bytes, private_key: bytes) -> str:
    # ダミー実装: メッセージの先頭8文字と "sig" を返す
    return message.decode('utf-8')[:8] + "_sig"

def verify(message: bytes, signed_message: str, public_key: bytes) -> bool:
    # ダミー実装: 先頭8文字＋"_sig" が一致すれば True
    expected = message.decode('utf-8')[:8] + "_sig"
    return signed_message == expected
