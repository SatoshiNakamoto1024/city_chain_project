# login_app/register.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import uuid
import logging
import base64
import qrcode
from io import BytesIO
from flask import Blueprint, request, jsonify, render_template

# テンプレートファイルは "template" フォルダ内に配置
template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "template"))
register_bp = Blueprint("register_bp", __name__, template_folder=template_path)

# ユーザー登録処理は registration/app_registration.py の register_user_interface 経由で行う
from registration.app_registration import register_user_interface as register_user

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@register_bp.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # ✅ 両対応
        if request.content_type and request.content_type.startswith("application/json"):
            data = request.get_json()
        else:
            data = request.form.to_dict()
            
        if not data:
            return jsonify({"error": "No data provided"}), 400

        try:
            result = register_user(data)
            # 証明書確認URL（後で証明書情報取得用のエンドポイントへ誘導）
            certificate_url = f"http://localhost:5000/certificate/info?uuid={result['uuid']}"
            # QRコード生成（Base64 Data URI）
            # register_user の戻り値にはすでに 'uuid', 'fingerprint' が入ってる前提で
            user_qr_payload = {
                "uuid": result["uuid"],
                "fingerprint": result["fingerprint"],
            }
            qr_json = json.dumps(user_qr_payload)
            qr_b64 = base64.b64encode(qr_json.encode("utf-8")).decode("utf-8")
            qr_img_data_uri = generate_qr_code(qr_b64)  # QRコードにBase64文字列を埋め込む

            result.update({
                "certificate_url": certificate_url,
                "qr_code": qr_img_data_uri
            })
            return jsonify(result), 200
        except Exception as e:
            logger.error("Registration error: %s", e)
            return jsonify({"error": str(e)}), 500
    else:
        return render_template("register.html")

def generate_qr_code(data: str) -> str:
    """
    与えられたURLをQRコードに変換し、Base64 Data URI形式で返す。
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"
