# CA/serve_ca.py
import os, sys, base64
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from CA.app_ca import generate_certificate_interface

app = Flask(__name__)

# ----------------------------------------------------------
# /ca/generate  : POST で証明書発行
#                JSON body:
#                 {
#                   "uuid": "<user_uuid>",
#                   "ntru_public": "<base64>",
#                   "dilithium_public_hex": "<hex str>",
#                   "validity_days": 365
#                 }
# ----------------------------------------------------------
@app.route("/ca/generate", methods=["POST"])
def ca_generate():
    if not request.is_json:
        raise BadRequest("Expecting application/json")

    j = request.get_json()
    try:
        user_uuid  = j["uuid"]
        ntru_pub_b64 = j["ntru_public"]
        dil_pub_hex  = j["dilithium_public_hex"]
        validity = int(j.get("validity_days", 365))
    except (KeyError, ValueError) as e:
        raise BadRequest(f"Invalid JSON fields: {e}")

    try:
        ntru_pub_bytes = base64.b64decode(ntru_pub_b64)
    except Exception as e:
        raise BadRequest(f"Bad ntru_public: {e}")

    cert_bytes, fp_hex = generate_certificate_interface(
        user_uuid, ntru_pub_bytes, dil_pub_hex, validity
    )

    return jsonify({
        "success": True,
        "certificate": base64.b64encode(cert_bytes).decode(),
        "fingerprint": fp_hex
    })

# ----------------------------------------------------------
# エントリーポイント
# ----------------------------------------------------------
if __name__ == "__main__":
    host = os.environ.get("CA_HOST", "0.0.0.0")
    port = int(os.environ.get("CA_PORT", 7000))
    debug = bool(int(os.environ.get("CA_DEBUG", "1")))
    app.run(host=host, port=port, debug=debug)
