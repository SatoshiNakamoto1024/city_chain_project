# auth_py/client_cert/certificate_info.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))  # プロジェクトルートをパスに追加

import logging
from flask import Blueprint, request, jsonify, render_template, redirect
from registration.app_registration import generate_qr_s3_url_interface
from registration.app_registration import get_certificate_interface  # 証明書メタデータ取得関数

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

cert_bp = Blueprint("cert_bp", __name__, template_folder="templates")


@cert_bp.route("/info", methods=["GET"])
def certificate_info():
    """
    GET /certificate/info?uuid=<uuid>
    uuid パラメータ必須。外部サービスから証明書情報を取得し、HTMLを返す。
    """
    user_uuid = request.args.get("uuid")
    if not user_uuid:
        return jsonify({"error": "uuid is required"}), 400

    try:
        cert = get_certificate_interface(user_uuid)
        if not cert:
            return jsonify({"error": "certificate not found"}), 404

        # HTMLテンプレートに `cert` として渡す
        return render_template("certificate_info.html", cert=cert), 200
    except Exception as e:
        logger.error("certificate_info error: %s", e)
        return jsonify({"error": str(e)}), 400


@cert_bp.route("/download_qr", methods=["GET"])
def download_qr():
    """
    GET /certificate/download_qr?uuid=<uuid>
    ユーザーUUIDに基づくQRコードをS3に再生成・アップロードし、そのURLへリダイレクト。
    """
    user_uuid = request.args.get("uuid")
    if not user_uuid:
        return jsonify({"error": "uuid is required"}), 400

    try:
        # S3にQR画像をアップロードし、公開URLを取得
        url = generate_qr_s3_url_interface(user_uuid, user_uuid)
        logger.info(f"QRコード再発行成功: {url}")
        return redirect(url)
    except Exception as e:
        logger.error("QRコード再発行エラー: %s", e)
        return jsonify({"error": str(e)}), 500


@cert_bp.route("/list", methods=["GET"])
def certificate_list():
    """
    クライアント証明書一覧（HTMLテーブル）
    """
    try:
        items = table.scan().get("Items", [])
        return render_template("certificate_list.html", certs=items)
    except Exception as e:
        logger.error("certificate_list error: %s", e)
        return jsonify({"error": str(e)}), 500
