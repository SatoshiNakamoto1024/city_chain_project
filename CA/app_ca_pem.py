# app_ca_pem.py\
"""
PEM 証明書発行専用 CA サーバ（本番用）
POST /ca/generate_pem でクライアント証明書を返す
"""
import os, sys, base64, json
from pathlib import Path
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest

# プロジェクトルートを sys.path に追加
BASE = Path(__file__).parent
sys.path.append(str(BASE))

from ca_generate_cert_asn1 import generate_root_cert
from ca_issue_client_cert_asn1 import issue_client_cert

print("app_ca_pem.py loaded")

app = Flask(__name__)

@app.route("/ca/generate_pem", methods=["POST"])
def generate_pem():
    if not request.is_json:
        raise BadRequest("Expecting application/json")

    j = request.get_json()
    try:
        uuid_str   = j["uuid"]
        ntru_pub_b = base64.b64decode(j["ntru_public_b64"])
        dil_pub_b  = bytes.fromhex(j["dil_public_hex"])
    except Exception as e:
        raise BadRequest(f"bad json: {e}")

    # 初回呼び出し時にルートCAを作成しておく
    generate_root_cert()  

    pem = issue_client_cert(ntru_pub_b, dil_pub_b, uuid_str)
    return jsonify({
        "success": True,
        "pem": pem.decode()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7001, debug=False)
