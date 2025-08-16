# registration/routes.py
from flask import Blueprint, request, jsonify, render_template
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

registration_bp = Blueprint("registration_bp", __name__, template_folder="templates")

@registration_bp.route("/", methods=["GET", "POST"], strict_slashes=False)
def registration_index():
    if request.method == "POST":
        # ✅ 両対応
        if request.content_type and request.content_type.startswith("application/json"):
            data = request.get_json()
        else:
            data = request.form.to_dict()
            
        if not data:
            return jsonify({"error": "No data provided"}), 400
        try:
            # interface 経由で登録処理を呼び出す
            from registration.app_registration import register_user_interface
            result = register_user_interface(data)
            return jsonify(result), 200
        except Exception as e:
            import traceback
            traceback.print_exc()  # ⭐ これを追加
            logger.error("登録失敗: %s", str(e))
            return jsonify({"success": False, "error": str(e)}), 500
    else:
        return render_template("register.html")


@registration_bp.route("/revoke_cert", methods=["POST"])
def revoke_cert():
    """
    POST /revoke_cert
      JSON: { "uuid": "..." }

    - 該当ユーザーの証明書を revoked = True に更新
    - revoked_at も付ける
    """
    data = request.get_json(silent=True) or {}
    uuid = data.get("uuid")
    if not uuid:
        return jsonify({"error": "uuid is required"}), 400

    try:
        now = datetime.now(timezone.utc).isoformat()
        users_table.update_item(
            Key={"uuid": uuid, "session_id": "REGISTRATION"},
            UpdateExpression="SET certificate.revoked = :r, certificate.revoked_at = :t",
            ExpressionAttributeValues={
                ":r": True,
                ":t": now
            }
        )
        return jsonify({"success": True, "revoked_at": now}), 200
    except Exception as e:
        logger.error(f"証明書失効エラー: {e}")
        return jsonify({"error": "revoke failed", "detail": str(e)}), 500
