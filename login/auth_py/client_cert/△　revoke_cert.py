# auth_py/client_cert/revoke_cert.py
import sys, os, logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import boto3
from flask import Blueprint, request, jsonify, redirect, url_for

from auth_py.config import AWS_REGION, USERS_TABLE_NAME

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client_cert_bp = Blueprint("client_cert_bp", __name__, template_folder="templates")

# DynamoDB table
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USERS_TABLE_NAME)

@client_cert_bp.route("/revoke_cert", methods=["POST"])
def revoke_cert_handler():
    user_uuid = request.form.get("user_uuid")
    if not user_uuid:
        return jsonify({"success": False, "error": "user_uuid is required"}), 400

    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        users_table.update_item(
            Key={"uuid": user_uuid, "session_id": "REGISTRATION"},
            UpdateExpression="SET certificate.revoked = :r, certificate.revoked_at = :t",
            ExpressionAttributeValues={
                ":r": True,
                ":t": now_iso,
            }
        )
        logger.info(f"証明書を失効しました: {user_uuid}")
        return redirect(url_for("profile_bp.profile", uuid=user_uuid))
    except Exception as e:
        logger.error(f"証明書失効エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
