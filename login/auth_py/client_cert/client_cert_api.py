# client_cert/client_cert_api.py
import sys, os, base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, request, jsonify

from client_cert.client_keygen import generate_client_keys
from auth_py.client_cert.client_cert import generate_client_certificate

app = Flask(__name__)

@app.route("/issue_cert", methods=["POST"])
def issue_cert():
    user_id = request.json.get("uuid")
    if not user_id:
        return jsonify({"error": "uuid required"}), 400

    # ① 端末用 PQC 鍵ペアを発行（NTRU + Dilithium）
    keys = generate_client_keys()

    # ② クライアント証明書を JSON‑bytes で生成
    cert_bytes, fp = generate_client_certificate(
        uuid_val=user_id,
        validity_days=request.json.get("validity_days", 365)   # 任意パラメータ
    )
    cert_b64 = base64.b64encode(cert_bytes).decode()

    return jsonify({
        "uuid":              user_id,
        "fingerprint":       fp,
        "client_cert":       cert_b64,                  # ← Base64(JSON)
        "ntru_private":      keys["ntru_private"].hex(),
        "dilithium_private": keys["dilithium_private"].hex()
    }), 200


if __name__ == "__main__":
    app.run(port=7000, debug=True)
