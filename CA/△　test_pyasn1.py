# CA/test_pyasn1.py
import sys
import os
from pathlib import Path
import base64

# pyasn1 modules
sys.path.insert(0, os.path.abspath(r"D:\city_chain_project\CA\pyasn1-master"))
from pyasn1.codec.der import decoder
sys.path.insert(0, os.path.abspath(r"D:\city_chain_project\CA\pyasn1-modules-master"))
from pyasn1_modules import rfc5280

# 1) load PEM and strip headers
pem_path = Path(r"D:\city_chain_project\CA\client_certs\client_demo_6df7fb61cb144054bcbfe87b62195733.pem")
b64 = "".join(
    line for line in pem_path.read_text().splitlines()
    if not line.startswith("-----")
)
der = base64.b64decode(b64)

# 2) decode with X.509 spec
cert, _ = decoder.decode(der, asn1Spec=rfc5280.Certificate())
tbs   = cert["tbsCertificate"]

# 3) SubjectPublicKeyInfo の取り出し
spki = tbs.getComponentByName("subjectPublicKeyInfo")
if spki is None or not spki.isValue:
    print("❌ SubjectPublicKeyInfo が存在しません。")
    sys.exit(1)

# Algorithm OID の表示
alg_oid = str(spki["algorithm"]["algorithm"])
print(f"🔑 公開鍵アルゴリズム OID = {alg_oid}")

# ✅ NTRU 公開鍵（BIT STRING）
ntru_pub_bitstring = spki["subjectPublicKey"]
ntru_pub_bytes = ntru_pub_bitstring.asOctets()
print(f"\n=== NTRU 公開鍵（hex）===\n{ntru_pub_bytes.hex()}")

# ✅ Dilithium 公開鍵（parameters に格納された OctetString）
params = spki["algorithm"].getComponentByName("parameters")
if params is None or not params.isValue:
    print("\n❌ Dilithium 公開鍵が parameters に見つかりませんでした。")
else:
    dilithium_pub_bytes = bytes(params)
    print(f"\n=== Dilithium 公開鍵（hex）===\n{dilithium_pub_bytes.hex()}")
