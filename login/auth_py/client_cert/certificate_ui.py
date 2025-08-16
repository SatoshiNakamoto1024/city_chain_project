# auth_py/client_cert/certificate_ui.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import boto3
from flask import Blueprint, render_template, jsonify
import logging
from auth_py.config import AWS_REGION, DYNAMODB_TABLE

# ──────────────────────────────────────────────
# ロガー設定
# ──────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ──────────────────────────────────────────────
# DynamoDB 初期化
# ──────────────────────────────────────────────
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

# ──────────────────────────────────────────────
# Blueprint
# ──────────────────────────────────────────────
cert_ui_bp = Blueprint("cert_ui_bp", __name__, template_folder="templates")

# ──────────────────────────────────────────────
# /certificate/list : クライアント証明書一覧表示
# ──────────────────────────────────────────────
@cert_ui_bp.route("/certificate/list", methods=["GET"])
def show_certificate_list():
    """
    クライアント証明書一覧ページ（管理者向け）
    """
    try:
        response = table.scan(
            FilterExpression="session_id = :sid",
            ExpressionAttributeValues={":sid": "CLIENT_CERT"}
        )
        certs = response.get("Items", [])
        logger.info("クライアント証明書 %d 件取得", len(certs))
        return render_template("certificate_list.html", certs=certs)
    except Exception as e:
        logger.error("一覧取得エラー: %s", e)
        return jsonify({"error": str(e)}), 500
