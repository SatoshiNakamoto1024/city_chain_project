# test_extract_extension.py
import sys
import base64
from pathlib import Path
from pyasn1.codec.der import decoder, encoder
from pyasn1_modules import rfc5280

def load_pem(pem_path: Path) -> bytes:
    print(f"[STEP] PEMファイルロード開始: {pem_path}")
    pem = pem_path.read_bytes()
    der_bytes = b''.join(
        base64.b64decode(line)
        for line in pem.splitlines()
        if b'-----' not in line
    )
    print(f"[STEP] PEM→DER変換完了。DER長: {len(der_bytes)} bytes")
    return der_bytes

def extract_dilithium_pub_manual(der_bytes: bytes) -> bytes:
    from pyasn1.type import univ

    OID_DIL_PUB = "1.3.6.1.4.1.99999.1.2"

    print("[STEP 1] 証明書全体をデコード")
    cert, remain = decoder.decode(der_bytes, asn1Spec=rfc5280.Certificate())
    print(f"[DEBUG] 残りバイト数 after cert decode: {len(remain)}")

    tbs = cert.getComponentByName('tbsCertificate')
    print(f"[DEBUG] tbsCertificate type: {type(tbs)}")

    print("[STEP 2] 拡張フィールド（position 9）を取得")
    exts_raw = tbs.getComponentByPosition(9)
    print(f"[DEBUG] 拡張（tag付き）type: {type(exts_raw)}")
    print(f"[DEBUG] 拡張 tagSet: {exts_raw.getTagSet()}")

    print("[STEP 3] EXPLICITタグを unwrap（生DERで取り出し）")
    try:
        # Extensions部分を Any 型でデコード（明示タグを剥がすため）
        exts_any, remain = decoder.decode(
            encoder.encode(exts_raw),
            asn1Spec=univ.Any()
        )
        exts_der = exts_any.asOctets()

        print(f"[DEBUG] unwrap後 DER長: {len(exts_der)} bytes")
        
        # unwrapされた拡張群をデコード
        real_exts, remain2 = decoder.decode(exts_der, asn1Spec=rfc5280.Extensions())
        print(f"[DEBUG] Extensions配列 decode完了。残り: {len(remain2)} bytes")
        print(f"[DEBUG] Extensions 要素数: {len(real_exts)}")

    except Exception as e:
        raise RuntimeError(f"[FAIL] unwrap/decode error at Extensions: {e}")

    print("[STEP 4] 拡張OIDごとに走査して Dilithium拡張を探す")
    for idx in range(len(real_exts)):
        try:
            ext = real_exts.getComponentByPosition(idx)
            if not ext.hasValue():
                print(f"[DEBUG] ext[{idx}] 空スロット、スキップ")
                continue
            oid = str(ext.getComponentByName('extnID'))
            print(f"[DEBUG] ext[{idx}] OID={oid}")

            if oid == OID_DIL_PUB:
                pub = ext.getComponentByName('extnValue').asOctets()
                print(f"[OK] Dilithium 公開鍵(先頭32B): {pub[:32].hex()}")
                return pub

        except Exception as e:
            print(f"[DEBUG] ext[{idx}] 読み込み失敗: {e}")
            break

    raise ValueError(f"[FAIL] Dilithium拡張 {OID_DIL_PUB} が見つかりませんでした")

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_extract_extension.py <path_to_pem>")
        return

    pem_path = Path(sys.argv[1])
    if not pem_path.exists():
        print(f"[ERROR] ファイルが存在しません: {pem_path}")
        return

    der_bytes = load_pem(pem_path)

    try:
        pub = extract_dilithium_pub_manual(der_bytes)
        print(f"[SUCCESS] Dilithium 公開鍵取得成功: {pub[:20].hex()} ...")
    except Exception as e:
        print(f"[ERROR] 最後のエラー: {e}")

if __name__ == "__main__":
    main()
