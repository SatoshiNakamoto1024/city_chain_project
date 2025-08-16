# auth_py/client_cert/certificate_info.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))  # プロジェクトルートをパスに追加

import logging
from flask import Blueprint, request, jsonify, render_template

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
