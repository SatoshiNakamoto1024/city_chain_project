# municipality_verification/approval_api.py

"""
市町村職員 (role=staff) 専用 承認 REST API
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Blueprint, request, jsonify, g
from login_app.decorators import require_role      # 「staff」で認証を行うためのデコレータ
from municipality_verification.verification import (
    get_pending_users, approve_user, reject_user
)
from municipality_verification.municipality_tools.municipality_approval_logger import (
    log_approval
)

approve_bp = Blueprint("approve_bp", __name__)

# ---------------------------------------------------- 一覧取得
@approve_bp.get("/staff/verify")
@require_role("staff")
def list_pending():
    """
    GET /staff/verify
    - require_role("staff") により、事前に staff_jwt が正しいかチェック済み
    - 承認待ちユーザー一覧（uuid のリスト）を返却
    """
    return jsonify(get_pending_users())


# ---------------------------------------------------- 承認/却下
@approve_bp.post("/staff/verify")
@require_role("staff")
def verify():
    """
    POST /staff/verify
    - require_role("staff") で JWT 検証済み、g.current_user_uuid に staff_id が入っている
    - JSON ボディで {uuid: ..., action: "approve" or "reject"} を受け取る
    """
    data      = request.get_json(silent=True) or request.form.to_dict()
    uuid_val  = data.get("uuid")
    action    = data.get("action")

    if not uuid_val or action not in ("approve", "reject"):
        return jsonify({"error": "uuid & action required"}), 400

    if action == "approve":
        approve_user(uuid_val)
    else:
        reject_user(uuid_val)

    # 承認ログを残す
    log_approval(
        uuid_val,
        action,
        approver_id = g.current_user_uuid,
        client_ip   = request.remote_addr
    )
    return jsonify({"success": True})
