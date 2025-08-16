# municipality_verification/municipality_views.py
from __future__ import annotations
import os, sys, logging
from flask import Blueprint, render_template, request, jsonify, g

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# ↓ import パスを municipality_tools に統一
from municipality_verification.municipality_tools.jwt_utils      import verify_admin_jwt
from municipality_verification.municipality_tools.approval_logger import log_approval
from municipality_verification.municipality_verification          import (
    get_pending_users, approve_user, reject_user
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

municipality_verify_bp = Blueprint(
    "municipality_verify_bp", __name__,
    template_folder="../../templates"
)

@municipality_verify_bp.route("/", methods=["GET"])
def municipality_verify_index():
    try:
        users = get_pending_users()
        return render_template(
            "municipality_verify.html",
            users=users,
            message="",
            error="",
            mapping_api_root="/mapping"   # ← 追加：テンプレート側で JS が使う
        )
    except Exception as e:
        logger.error("承認待ちユーザー一覧取得エラー: %s", e)
        return render_template(
            "municipality_verify.html",
            users=[],
            error=str(e),
            message="",
            mapping_api_root="/mapping"
        )

@municipality_verify_bp.route("/", methods=["POST"])
def municipality_verify_action():
    """
    POSTアクセスで承認・却下を処理。
    ただし、リクエストヘッダーに 'Authorization: Bearer <token>' が必要。
    """
    uuid = request.form.get("uuid")
    action = request.form.get("action")
    approval_code = request.form.get("approval_code")

    # 認証用トークンの取り出し
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    admin_id = verify_admin_jwt(token)

    if not admin_id:
        # JWT が不正または期限切れの場合
        users = get_pending_users()
        return render_template(
            "municipality_verify.html",
            users=users,
            error="職員認証に失敗しました（トークン不正または期限切れ）",
            message=""
        )

    if not uuid or action not in ["approve", "reject"]:
        users = get_pending_users()
        return render_template(
            "municipality_verify.html",
            users=users,
            error="UUIDとアクションが必要です",
            message=""
        )

    try:
        if action == "approve":
            if approval_code != "APPROVED":
                # 承認コード不一致 → 却下扱いとしてログ
                log_approval(
                    uuid=uuid,
                    action="rejected",
                    approver_id=admin_id,
                    reason="承認コード不一致",
                    client_ip=request.remote_addr
                )
                users = get_pending_users()
                return render_template(
                    "municipality_verify.html",
                    users=users,
                    error="承認コードが正しくありません",
                    message=""
                )

            # 正しい承認コードの場合は承認
            approve_user(uuid)
            log_approval(
                uuid=uuid,
                action="approved",
                approver_id=admin_id,
                reason="本人確認成功",
                client_ip=request.remote_addr
            )
            message = f"ユーザー {uuid} を承認しました。"

        else:  # action == "reject"
            reject_user(uuid)
            log_approval(
                uuid=uuid,
                action="rejected",
                approver_id=admin_id,
                reason="職員による却下",
                client_ip=request.remote_addr
            )
            message = f"ユーザー {uuid} を却下しました。"

        users = get_pending_users()
        return render_template("municipality_verify.html", users=users, message=message, error="")

    except Exception as e:
        logger.error("本人確認エラー: %s", e)
        users = get_pending_users()
        return render_template("municipality_verify.html", users=users, error=str(e), message="")
