import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import logging
from flask import Blueprint, render_template, request, jsonify
from login_app.municipality_verification.verification import get_pending_users, approve_user, reject_user
from login_app.municipality_verification.admin_tools.approval_logger import log_approval
from login_app.municipality_verification.admin_login import verify_admin_jwt

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

municipality_verify_bp = Blueprint("municipality_verify_bp", __name__, template_folder="templates")

# ✅ UI 画面：市町村職員が目で照合し、承認／却下する
@municipality_verify_bp.route("/ui", methods=["GET", "POST"])
def municipality_verify_ui():
    if request.method == "POST":
        uuid = request.form.get("uuid")
        action = request.form.get("action")

        if not uuid or action not in ["approve", "reject"]:
            return jsonify({"error": "UUIDとアクションが必要です"}), 400

        try:
            if action == "approve":
                approve_user(uuid)
                message = f"ユーザー {uuid} を承認しました。"
            else:
                reject_user(uuid)
                message = f"ユーザー {uuid} を却下しました。"
            return render_template("municipality_verify.html", users=get_pending_users(), message=message)
        except Exception as e:
            logger.error("承認エラー: %s", e)
            return render_template("municipality_verify.html", users=get_pending_users(), error=str(e))
    else:
        users = get_pending_users()
        return render_template("municipality_verify.html", users=users)


# ✅ API 形式：approval_code を照合して自動認証（スマホや自動化対応用）
@municipality_verify_bp.route("/code_verify", methods=["POST"])
def municipality_code_verify():
    approval_code = request.form.get("approval_code")
    uuid_to_verify = request.form.get("uuid")
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    admin_id = verify_admin_jwt(token)

    if not admin_id:
        return jsonify({"error": "職員認証に失敗しました"}), 401

    if approval_code == "APPROVED":
        log_approval(uuid=uuid_to_verify, action="approved", approver_id=admin_id,
                     reason="本人確認OK", client_ip=request.remote_addr)
        return jsonify({"uuid": uuid_to_verify, "approved": True})
    else:
        log_approval(uuid=uuid_to_verify, action="rejected", approver_id=admin_id,
                     reason="承認コード不一致", client_ip=request.remote_addr)
        return jsonify({"error": "承認コードが正しくありません。"}), 400
