# login/auth_py/make_register_body.py
import json
from pathlib import Path

def main():
    # PEMファイルパス
    pem_path = input("クライアント証明書 (PEM) ファイルパスを入力してください: ").strip()

    # ユーザー名とパスワードを入力
    username = input("登録するユーザー名を入力してください: ").strip()
    password = input("登録するパスワードを入力してください: ").strip()

    # PEMファイル読み込み
    try:
        client_cert_pem = Path(pem_path).read_text(encoding="utf-8")
    except Exception as e:
        print(f"[エラー] PEMファイルの読み込みに失敗: {e}")
        return

    # body生成
    body = {
        "username": username,
        "password": password,
        "client_cert_pem": client_cert_pem.strip()
    }

    # 保存するか？
    save = input("生成したJSONをファイル保存しますか？ (y/n): ").strip().lower()

    if save == "y":
        save_path = f"register_body_{username}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False, indent=2)
        print(f"[OK] {save_path} に保存しました。")
    else:
        print("\n=== 生成されたJSON ===\n")
        print(json.dumps(body, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
