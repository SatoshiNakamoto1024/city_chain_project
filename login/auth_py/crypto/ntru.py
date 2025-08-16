# login/auth_py/crypto/ntru.py
import os
import sys

# 本物のD:\city_chain_project\ntru\ntru-pyを読み込み
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\ntru-py"))

from ntru_encryption import NtruEncryption

__all__ = ["NtruEncryption"]
