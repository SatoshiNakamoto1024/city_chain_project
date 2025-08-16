# File: client_code/pc_check.py

"""
PC/IoT 家電用クライアントスクリプト（本番実装用）

ワークフロー:
 1. 起動時に dummy100mb.bin を生成して 100 MB を占有
 2. 空き容量を測定してサーバーへ POST
 3. サーバーから認証成功レスポンスを受けたら dummy100mb.bin を削除
 4. 次回起動時に再び (1) に戻る
"""

import os
import requests
import shutil
import sys

# サーバーの「デバイス認証＋ストレージチェック」エンドポイント
SERVER_URL = "http://127.0.0.1:5050/device_auth/login"

# ダミーファイル設定
DUMMY_FILENAME = "dummy100mb.bin"
DUMMY_SIZE = 100 * 1024 * 1024  # 100MB

def ensure_dummy_file(directory: str = None) -> str:
    """
    directory 配下に DUMMY_FILENAME を作成して DUMMY_SIZE バイトを確保。
    既存ファイルがサイズ未満なら再生成。
    Returns the full path to the dummy file.
    """
    if directory is None:
        directory = os.getcwd()
    path = os.path.join(directory, DUMMY_FILENAME)

    # ファイルがなければ作成、サイズ不足なら拡張
    if not os.path.exists(path) or os.path.getsize(path) < DUMMY_SIZE:
        with open(path, "wb") as f:
            f.seek(DUMMY_SIZE - 1)
            f.write(b"\0")

    return path

def remove_dummy_file(directory: str = None) -> None:
    """
    directory 配下の DUMMY_FILENAME を削除 (存在すれば)。
    """
    if directory is None:
        directory = os.getcwd()
    path = os.path.join(directory, DUMMY_FILENAME)
    if os.path.exists(path):
        os.remove(path)

def get_free_space(path: str = "/") -> int:
    """
    指定パスの空きバイト数を返す。
    """
    total, used, free = shutil.disk_usage(path)
    return free

def main():
    # 1) ダミーファイル生成 (常に 100MB を占有)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dummy_path = ensure_dummy_file(directory=script_dir)

    # 2) 空き容量取得 (dummyファイルを置いたディレクトリを計測)
    free_bytes = get_free_space(script_dir)
    print(f"[Client] Free space after dummy allocation: {free_bytes} bytes")

    # 3) サーバーへ認証＋ストレージ情報を送信
    username = "admin"
    password = "password"
    payload = {
        "username": username,
        "password": password,
        "client_free_space": free_bytes
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    resp = requests.post(SERVER_URL, json=payload, headers=headers)
    print(f"[Client] Server response: {resp.status_code} / {resp.text}")

    # 4) 認証成功ならダミーファイルを削除して領域を開放
    try:
        body = resp.json()
    except ValueError:
        body = {}

    if resp.status_code == 200 and body.get("success") is True:
        print("[Client] Login successful → removing dummy file")
        remove_dummy_file(directory=script_dir)
    else:
        print("[Client] Login failed or storage check failed → dummy file retained")

if __name__ == "__main__":
    sys.exit(main())
