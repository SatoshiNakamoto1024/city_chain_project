# login/auth_py/client_cert/client_keygen.py
import sys, os
sys.path += [
    r"D:\city_chain_project\ntru\ntru-py",
    r"D:\city_chain_project\ntru\dilithium-py"
]
from ntru_encryption import NtruEncryption
from app_dilithium   import create_keypair as create_dil

ntru = NtruEncryption()

def generate_client_keys():
    # NTRU
    kp = ntru.generate_keypair()
    ntru_pub  = bytes(kp["public_key"])
    ntru_priv = bytes(kp["secret_key"])

    # Dilithium
    dil_pub, dil_priv = map(bytes, create_dil())

    return {
        "ntru_public":  ntru_pub,
        "ntru_private": ntru_priv,
        "dilithium_public":  dil_pub,
        "dilithium_private": dil_priv
    }
