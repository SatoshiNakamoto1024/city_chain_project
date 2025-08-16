# client_cert/client_keygen.py

import sys
import os
import json

# NTRUモジュールの読み込み
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\ntru-py"))
from ntru_encryption import NtruEncryption
ntru = NtruEncryption()

# Dilithiumモジュールの読み込み
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\dilithium-py"))
from app_dilithium import create_keypair as create_dilithium

def generate_client_keys():
    # 🔐 NTRU鍵生成（NtruEncryptionクラス経由）
    keypair = ntru.generate_keypair()  # generate_ntru_keypair
    ntru_pub = keypair["public_key"]
    ntru_priv = keypair["secret_key"]

    # 🔐 Dilithium鍵生成
    dil_pub, dil_priv = create_dilithium()

    return {
        "ntru_public": ntru_pub,
        "ntru_private": ntru_priv,
        "dilithium_public": bytes(dil_pub).hex() if isinstance(dil_pub, list) else dil_pub.hex(),
        "dilithium_private": bytes(dil_priv).hex() if isinstance(dil_priv, list) else dil_priv.hex()
    }
