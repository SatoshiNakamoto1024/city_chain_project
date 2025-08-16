# ca/ca_keygen.py
import sys
import os
sys.path.append(os.path.abspath("D:\\city_chain_project\\ntru\\ntru-py"))
from ntru_encryption import generate_keypair # generate_ntru_keypair
import json
from datetime import datetime

def save_ca_keys():
    pub, priv = generate_keypair() # generate_ntru_keypair

    os.makedirs("ca/keys", exist_ok=True)

    with open("ca/keys/ca_public.json", "w") as f:
        json.dump({"created": datetime.utcnow().isoformat(), "key": pub}, f)

    with open("ca/keys/ca_private.json", "w") as f:
        json.dump({"created": datetime.utcnow().isoformat(), "key": priv}, f)

    print("CA鍵ペアを保存しました")

if __name__ == "__main__":
    save_ca_keys()
