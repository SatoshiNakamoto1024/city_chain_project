# admin/admin_routes.py
import sys, os, time, json, base64, logging
from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt
from boto3 import resource as boto3_resource

from registration.pairing_token import create_pairing_token
from device_manager.app_device_manager import (
    register_device_interface,
    revoke_device_interface,
    revoke_all_devices_for_user_interface,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

admin_bp = Blueprint(
    "admin_bp",
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
)

# DynamoDB テーブル名は設定から取得
from login_app.config import AWS_REGION, DEVICES_TABLE
dynamodb = boto3_resource("dynamodb", region_name=AWS_REGION)
devices_table = dynamodb.Table(DEVICES_TABLE)


def _assert_admin():
    claims = get_jwt()
    if not claims.get("admin"):
        raise PermissionError("admin privileges required")


@admin_bp.route("/issue_qr", methods=["GET"])
@jwt_required()
def issue_qr_form():
    _assert_admin()
    return render_template("admin_issue_qr.html")


@admin_bp.route("/issue_qr", methods=["POST"])
@jwt_required()
def issue_qr():
    _assert_admin()
    data = request.get_json(silent=True) or {}
    user_uuid = data.get("uuid")
    if not user_uuid:
        return jsonify({"error": "uuid is required"}), 400

    token = create_pairing_token(user_uuid, ttl=600)
    expires_at = int(time.time()) + 600
    qr_payload = {"uuid": user_uuid, "token": token, "expires_at": expires_at}
    qr_b64 = base64.b64encode(json.dumps(qr_payload).encode()).decode()

    logger.info("Admin issued new QR for uuid=%s expires_at=%d", user_uuid, expires_at)
    return jsonify({"qr_code": qr_b64, "expires_at": expires_at}), 200


@admin_bp.route("/revoke_device", methods=["GET"])
@jwt_required()
def revoke_device_form():
    _assert_admin()
    return render_template("admin_revoke_device.html")


@admin_bp.route("/revoke_device", methods=["POST"])
@jwt_required()
def revoke_device():
    _assert_admin()
    data = request.get_json(silent=True) or {}
    user_uuid = data.get("uuid")
    device_id = data.get("device_id")
    if not (user_uuid and device_id):
        return jsonify({"error": "uuid and device_id are required"}), 400

    try:
        # device_manager 側で失効処理を行う
        revoke_device_interface(user_uuid=user_uuid, device_id=device_id)
        logger.info("Admin revoked device: uuid=%s device_id=%s", user_uuid, device_id)
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("Failed to revoke device: %s", e)
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/reset_devices", methods=["GET"])
@jwt_required()
def reset_devices_form():
    _assert_admin()
    return render_template("admin_reset_devices.html")


@admin_bp.route("/reset_devices", methods=["POST"])
@jwt_required()
def reset_devices():
    _assert_admin()
    data = request.get_json(silent=True) or {}
    user_uuid = data.get("uuid")
    if not user_uuid:
        return jsonify({"error": "uuid is required"}), 400

    try:
        # device_manager 側で全端末一括失効
        revoke_all_devices_for_user_interface(user_uuid=user_uuid)
        logger.info("Admin reset all devices for uuid=%s", user_uuid)
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("Failed to reset devices: %s", e)
        return jsonify({"error": str(e)}), 500
