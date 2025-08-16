# login/auth_py/revoke_cert_service.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
from datetime import datetime, timezone
import logging
from flask import Blueprint, request, jsonify, redirect, url_for
from auth_py.config import DYNAMODB_TABLE

# CloudWatch Logs 連携
from auth_py.cloud_logging.cloud_logger import init_log_stream, log_to_cloudwatch
init_log_stream()  # 初期化（グループ/ストリーム作成）

# DynamoDB
dynamodb = boto3.resource("dynamodb")
users_table = dynamodb.Table(DYNAMODB_TABLE)

# Flask Blueprint
client_cert_bp = Blueprint("client_cert_bp", __name__, template_folder="templates")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def revoke_certificate_by_uuid(user_uuid: str):
    """
    内部サービス用：指定された UUID の証明書を失効状態にする。
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    response = users_table.update_item(
        Key={"uuid": user_uuid, "session_id": "REGISTRATION"},
        UpdateExpression="SET certificate.revoked = :r, certificate.revoked_at = :t",
        ExpressionAttributeValues={
            ":r": True,
            ":t": now_iso
        },
        ReturnValues="UPDATED_NEW"
    )

    #  CloudWatch ログ記録
    log_to_cloudwatch({
        "event": "revoke_cert",
        "uuid": user_uuid,
        "revoked_at": now_iso,
        "status": "success"
    })

    return response


@client_cert_bp.route("/revoke_cert", methods=["POST"])
def revoke_cert_handler():
    """
    外部 HTTP 用：POST /client_cert/revoke_cert
    UUIDを指定して証明書を失効状態にする
    """
    user_uuid = request.form.get("user_uuid")
    if not user_uuid:
        return jsonify({"success": False, "error": "user_uuid is required"}), 400

    try:
        revoke_certificate_by_uuid(user_uuid)
        logger.info(f"証明書を失効しました: {user_uuid}")
        return redirect(url_for("profile_bp.profile", uuid=user_uuid))

    except Exception as e:
        logger.error(f"証明書失効エラー: {e}")

        # CloudWatch ログ記録（エラー時）
        log_to_cloudwatch({
            "event": "revoke_cert",
            "uuid": user_uuid,
            "status": "failure",
            "error": str(e)
        })

        return jsonify({"success": False, "error": str(e)}), 500
