import requests
import pytest

BASE_URL = "http://localhost:5001"  # app.pyのサーバが動作しているURL


def test_generate_keys():
    # 鍵生成エンドポイントにリクエスト
    response = requests.get(f"{BASE_URL}/generate_keys")
    assert response.status_code == 200, "鍵生成エンドポイントが失敗しました。"

    # 応答データを解析
    data = response.json()
    assert "public_key" in data, "公開鍵が含まれていません。"
    assert "private_key" in data, "秘密鍵が含まれていません。"

    public_key = data["public_key"]
    private_key = data["private_key"]

    # 鍵の形式を確認
    assert isinstance(public_key, list), "公開鍵がリスト形式ではありません。"
    assert isinstance(private_key, list), "秘密鍵がリスト形式ではありません。"

    print("鍵生成テストに成功しました。")


def test_encrypt_and_decrypt():
    # 鍵を生成
    keys_response = requests.get(f"{BASE_URL}/generate_keys")
    assert keys_response.status_code == 200, "鍵生成が失敗しました。"
    keys = keys_response.json()

    public_key = keys["public_key"]
    private_key = keys["private_key"]

    message = "Test Message"

    # 暗号化
    encrypt_response = requests.post(
        f"{BASE_URL}/encrypt",
        json={"message": message, "public_key": public_key},
    )
    assert encrypt_response.status_code == 200, "暗号化エンドポイントが失敗しました。"

    encrypted_message = encrypt_response.json().get("encrypted_message")
    assert encrypted_message is not None, "暗号化されたメッセージがありません。"

    # 復号化
    decrypt_response = requests.post(
        f"{BASE_URL}/decrypt",
        json={
            "encrypted_message": encrypted_message, "private_key": private_key
        },
    )
    assert decrypt_response.status_code == 200, "復号化エンドポイントが失敗しました。"

    decrypted_message = decrypt_response.json().get("decrypted_message")
    assert decrypted_message == message, "復号化メッセージが一致しません。"

    print("暗号化と復号化テストに成功しました。")
