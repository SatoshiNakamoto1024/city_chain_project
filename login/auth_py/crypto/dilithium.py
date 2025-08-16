# login/auth_py/crypto/dilithium.py
import os
import sys

# ここでは ntru/dilithium-py の app_dilithium を使って
# create_keypair, sign_message, verify_signature を取り込む想定です:
try:
    # 通常インストールされた環境向け
    from app_dilithium import create_keypair, sign_message, verify_message as verify_signature
except ImportError:
    # もし相対パスで持ってきたいならこっちにパスを通す
    sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\dilithium-py"))
    from app_dilithium import create_keypair, sign_message, verify_message as verify_signature

__all__ = [
    'create_keypair',    # 鍵ペア生成
    'sign_message',      # メッセージ署名
    'verify_signature',  # 署名検証
]