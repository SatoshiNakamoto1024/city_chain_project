# municipality_verification/municipality_tools/municipality_register.py

import os
import hashlib
import boto3
import uuid

# もともとここに load_dotenv() があったが、テスト環境では不要なので削除

# 環境変数からテーブル名とリージョンを取得
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
STAFF_TABLE = os.getenv("STAFF_TABLE", "MunicipalStaffs")

# DynamoDB に接続
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(STAFF_TABLE)


def generate_salt() -> str:
    """
    16 バイトのランダムソルトを生成し、16進文字列（32文字）で返す。
    """
    return os.urandom(16).hex()


def hash_password(password: str, salt: str) -> str:
    """
    SHA-256 で (salt + password) をハッシュし、16 進文字列で返す。
    - salt は 16 進文字列（hex）である前提とする。
    """
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def register_staff(staff_id: str,
                   password: str,
                   name: str,
                   municipality: str) -> None:
    """
    DynamoDB の MunicipalStaffs テーブルに職員アカウントを登録する。
    - テーブルのプライマリキーは (staff_id: HASH, municipality: RANGE) を想定。
    """
    salt = generate_salt()
    password_hash = hash_password(password, salt)

    item = {
        "staff_id":      staff_id,
        "municipality":  municipality,
        "password_hash": password_hash,
        "salt":          salt,
        "name":          name
    }

    try:
        table.put_item(Item=item)
        print(f"[✓] 職員登録完了: {staff_id}（市町村: {municipality}）")
    except Exception as e:
        print(f"[✗] 職員登録失敗: {e}")


if __name__ == "__main__":
    """
    コマンドラインから直接実行したときの対話的登録処理
    """
    print("=== 職員アカウント登録 ===")
    staff_id = input("ユーザーID (staff_id): ").strip()
    password = input("パスワード: ").strip()
    name = input("職員名 (name): ").strip()
    municipality = input("所属市町村: ").strip()

    register_staff(staff_id, password, name, municipality)
