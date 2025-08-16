# File: network/sending_DAG/python_sending/cert_python/app_cert.py

"""
app_cert.py

コマンドラインで PEM を指定し、JSON メッセージの Dilithium 署名・検証を行うデモスクリプト。

使い方:
  python app_cert.py path/to/client.pem \
        --msg '{"tx_id":"abc123","nonce":12345}'

オプション:
  --msg  : 署名／検証対象の JSON 文字列。省略時はデフォルトサンプルを使用。
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import json
import base64
from pathlib import Path

# モジュール化した cert_python パッケージを import
from cert_python.cert_signer import sign_with_cert
from cert_python.cert_validator import verify_signature_with_cert

def main():
    parser = argparse.ArgumentParser(description="PQC 証明書 (Dilithium) 署名・検証デモ")
    parser.add_argument("pem", help="クライアント証明書 (PEM) ファイルのパス")
    parser.add_argument(
        "--msg", "-m",
        help="署名／検証対象のメッセージ (JSON 文字列)。省略時はデフォルトを使用。"
    )
    args = parser.parse_args()

    pem_path = Path(args.pem)
    if not pem_path.exists():
        print(f"Error: PEM ファイルが見つかりません: {pem_path}", file=sys.stderr)
        sys.exit(1)

    # メッセージ準備
    if args.msg:
        msg = args.msg
    else:
        # デフォルトサンプル
        msg = json.dumps({"tx_id": "abc123", "nonce": 12345}, ensure_ascii=False)

    print("=== Message ===")
    print(msg)
    print()

    # 1) 署名生成
    sig_bytes = sign_with_cert(msg, str(pem_path))
    b64_sig = base64.b64encode(sig_bytes).decode()
    print("=== Signature (base64) ===")
    print(b64_sig)
    print()

    # 2) 署名検証
    ok = verify_signature_with_cert(msg, b64_sig, str(pem_path))
    print("=== Verify Result ===")
    print("OK" if ok else "FAIL")


if __name__ == "__main__":
    main()
