# login_app/register.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import uuid
import logging
import base64
from io import BytesIO
from flask import Blueprint, request, jsonify, render_template

# QR コード生成に必須のライブラリ
import qrcode
from PIL import Image  # Pillow

# ユーザー登録処理
from registration.app_registration import register_user_interface as register_user
from wallet.wallet_service import create_wallet_for_user

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

register_bp = Blueprint("register_bp", __name__, template_folder="template")

@register_bp.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if request.content_type and request.content_type.startswith("application/json"):
            data = request.get_json()
        else:
            data = request.form.to_dict()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        try:
            result = register_user(data)
            
            # ★追加：ウォレット作成
            wallet = create_wallet_for_user(user_uuid=result["uuid"])
            result.update(
                wallet_address = wallet.wallet_address,
                balance        = float(wallet.balance)   # ★ Decimal → float
            )
            # ------------------------------------------------------------
            # ここで client_cert を “必ず” Base64‑JSON 形式に戻す
            #    もし登録モジュールが返したものが PEM だったら上書きし直す
            # ------------------------------------------------------------
            if not result.get("client_cert", "").startswith("ey"):  # PEMなら先頭は "-----"
                cert_dict = result["certificate"]                   # pem / fingerprint などが入った dict
                result["client_cert"] = base64.b64encode(
                  json.dumps(cert_dict, ensure_ascii=False).encode()
                ).decode()

            # 証明書確認用 URL
            certificate_url = f"http://localhost:5000/certificate/info?uuid={result['uuid']}"

            # ここから QR コード生成。失敗したら例外を吐いて 500 にする
            user_qr_payload = {
                "uuid": result["uuid"],
                "fingerprint": result["fingerprint"],
            }
            qr_json = json.dumps(user_qr_payload)
            qr_b64 = base64.b64encode(qr_json.encode("utf-8")).decode("utf-8")

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_b64)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            qr_img_data_uri = f"data:image/png;base64,{img_str}"

            result.update({
                "certificate_url": certificate_url,
                "qr_code": qr_img_data_uri
            })
            return jsonify(result), 200

        except Exception as e:
            logger.error("Registration error (including QR code generation): %s", e)
            return jsonify({"error": str(e)}), 500

    else:
        return render_template("register.html")
