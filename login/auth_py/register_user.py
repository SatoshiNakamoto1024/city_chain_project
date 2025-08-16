# login/auth_py/register_user.py
import json
import requests
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth_py.client_cert.app_client_cert import generate_client_keys_interface

def main():
    # 保存したJSONを読み込む
    with open("register_body_alice.json", "r", encoding="utf-8") as f:
        body = json.load(f)

    # FlaskサーバーのURL
    url = "http://localhost:5000/register"

    # POSTリクエスト
    response = requests.post(url, json=body)

    # レスポンス表示
    print("\n=== サーバー応答 ===\n")
    print(f"ステータスコード: {response.status_code}")
    print(response.text)

if __name__ == "__main__":
    main()
