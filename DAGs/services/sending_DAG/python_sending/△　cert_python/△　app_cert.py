# sending_DAG/python_sending/cert_python/app_cert.py
"""
python app_cert.py pem/client.pem
"""
import sys, base64, json
from pathlib import Path
from cert_python import sign_with_cert, verify_signature_with_cert

pem_path = Path(sys.argv[1])

msg = json.dumps({"tx_id":"abc123","nonce":12345})
sig = sign_with_cert(msg, pem_path)
b64 = base64.b64encode(sig).decode()

print("signature(base64)=", b64[:32]+"...")

ok  = verify_signature_with_cert(msg, b64, pem_path)
print("verify =", ok)
