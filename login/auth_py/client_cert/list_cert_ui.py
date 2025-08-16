# auth_py/client_cert/list_cert_ui.py

import sys, os, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import boto3
from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime, timezone
from auth_py.config import AWS_REGION, USERS_TABLE_NAME

admin_cert_bp = Blueprint("admin_cert_bp", __name__, template_folder="templates")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USERS_TABLE_NAME)

@admin_cert_bp.route("/admin/list", methods=["GET"])
def list_cert_admin():
    try:
        # REGISTRATION のみ一覧化
        response = users_table.scan(
            FilterExpression="session_id = :sid",
            ExpressionAttributeValues={":sid": "REGISTRATION"}
        )
        items = response.get("Items", [])
        return render_template("list_cert_admin.html", users=items)
    except Exception as e:
        logger.error(f"一覧取得失敗: {e}")
        return f"Error: {str(e)}", 500


@admin_cert_bp.route("/admin/revoke/<uuid>", methods=["POST"])
def revoke_from_admin(uuid):
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        users_table.update_item(
            Key={"uuid": uuid, "session_id": "REGISTRATION"},
            UpdateExpression="SET certificate.revoked = :r, certificate.revoked_at = :t",
            ExpressionAttributeValues={":r": True, ":t": now_iso}
        )
        logger.info(f"[Admin] 証明書失効: {uuid}")
        return redirect(url_for("admin_cert_bp.list_cert_admin"))
    except Exception as e:
        logger.error(f"[Admin] 失効エラー: {e}")
        return f"失効失敗: {str(e)}", 500
