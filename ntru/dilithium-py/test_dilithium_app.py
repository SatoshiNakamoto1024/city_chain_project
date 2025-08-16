import dilithium5


def test_sign_and_verify():
    # 鍵ペア生成
    pk, sk = dilithium5.generate_keypair()
    print(type(pk), type(sk))
    if isinstance(pk, list):
        pk = bytes(pk)  # リストをバイト列に変換
    if isinstance(sk, list):
        sk = bytes(sk)  # リストをバイト列に変換

    # メッセージ署名
    message = b"Hello Dilithium"
    signed_msg = dilithium5.sign(message, sk)
    if isinstance(signed_msg, list):
        signed_msg = bytes(signed_msg)  # 署名メッセージをバイト列に変換

    # 検証
    ok = dilithium5.verify(message, signed_msg, pk)
    assert ok is True, "should verify successfully"

    # 改ざんテスト
    tampered = b"Hello Tampered"
    ok = dilithium5.verify(tampered, signed_msg, pk)
    assert ok is False, "verification must fail for tampered message"
    print("Tampered message verification correctly failed.")

if __name__ == '__main__':
    test_sign_and_verify()
    print("All tests passed!")