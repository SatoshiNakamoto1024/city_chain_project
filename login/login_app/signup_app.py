# login_app/signup_app.py  ― UsersTable に uuid + session_id で書き込む
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid, hashlib, requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError
from login_app.config import AWS_REGION, USERS_TABLE, CLIENT_CERT_ENDPOINT

# DynamoDB
dynamodb     = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table  = dynamodb.Table(USERS_TABLE)

# Flask
app = Flask(__name__)
CORS(app)

def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

@app.route("/signup", methods=["POST"])
def signup():
    body = request.get_json() or {}
    if not {"username", "password"} <= body.keys():
        return jsonify({"error": "username and password are required"}), 400

    # ---- PK / SK を生成 ----
    user_uuid  = str(uuid.uuid4())
    session_id = "USER_PROFILE"          # 固定でも良いしデバイスIDでも良い

    # ---- 証明書発行 ----
    try:
        res = requests.get(
            CLIENT_CERT_ENDPOINT,
            params={"uuid": user_uuid, "validity_days": 365},
            timeout=5,
        )
        res.raise_for_status()
        cert = res.json()                # fingerprint / client_cert(Base64) 等
    except Exception as e:
        return jsonify({"error": "certificate service failed", "detail": str(e)}), 502

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    item = {
        "uuid":        user_uuid,        # ← HASH キー
        "session_id":  session_id,       # ← RANGE キー
        "username":    body["username"],
        "password_hash": _hash_pw(body["password"]),
        "created_at":  now_iso,
        "certificate": {
            "fingerprint": cert["fingerprint"],
            "client_cert": cert["client_cert"],  # Base64
            "issued_at":   now_iso,
            "revoked":     False,
            "revoked_at":  None,
        },
    }

    try:
        users_table.put_item(Item=item)
    except ClientError as e:
        return jsonify({"error": "dynamodb put_item failed", "detail": str(e)}), 500

    return jsonify(
        {
            "uuid":        user_uuid,
            "fingerprint": cert["fingerprint"],
            "issued_at":   now_iso,
        }
    ), 200


if __name__ == "__main__":
    app.run(debug=True, port=6010)
