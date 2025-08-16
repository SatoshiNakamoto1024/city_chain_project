# client_cert/cert_builder.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import uuid
from datetime import datetime, timedelta
from CA.ca_signer import sign_certificate

def build_client_certificate(user_id: str, ntru_pub: str, dil_pub: str) -> dict:
    cert = {
        "uuid": user_id,
        "ntru_public": ntru_pub,
        "dilithium_public": dil_pub,
        "valid_from": datetime.utcnow().isoformat(),
        "valid_to": (datetime.utcnow() + timedelta(days=365)).isoformat(),
        "issuer": "CustomCA v1"
    }
    return sign_certificate(cert)
