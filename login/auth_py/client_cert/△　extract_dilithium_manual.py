# extract_dilithium_manual.py
import base64
from pyasn1.codec.der import decoder
from pyasn1_modules import rfc5280

# PEMファイルからDER抽出
def load_pem(path: str) -> bytes:
    with open(path, 'rb') as f:
        pem = f.read()
    return b''.join(
        base64.b64decode(line)
        for line in pem.splitlines()
        if b"-----" not in line
    )

# EXPLICIT [3] を手動で剥がして Dilithium 拡張を探す
def extract_dilithium_pub_manual(der: bytes) -> bytes:
    OID_DIL = "1.3.6.1.4.1.99999.1.2"
    cert, _ = decoder.decode(der, asn1Spec=rfc5280.Certificate())
    tbs = cert['tbsCertificate']
    
    # 拡張部分（タグ付き）を取得し、明示的に decode
    ext_octets = tbs['extensions'].asOctets()
    extensions, _ = decoder.decode(ext_octets, asn1Spec=rfc5280.Extensions())

    for ext in extensions:
        if str(ext['extnID']) == OID_DIL:
            return ext['extnValue'].asOctets()
    
    raise ValueError("Dilithium 拡張が見つかりません")

# ===== 実行部分 =====
if __name__ == "__main__":
    pem_path = "D:/city_chain_project/CA/client_certs/client_demo_14faabfc990b4299a83e48647cf2659e.pem"
    der = load_pem(pem_path)
    pub = extract_dilithium_pub_manual(der)
    print(f"[OK] 拡張から抽出された公開鍵（先頭20バイト）: {pub[:20].hex()}")
