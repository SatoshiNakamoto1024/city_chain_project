# municipality_verification/views.py

"""
市町村側の「ユーザー承認」部分のビュー (Blueprint) 実装。
- /staff/verify に対する GET/POST を実装
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
from flask import Blueprint, render_template, request
import jwt
from municipality_verification.config import JWT_SECRET, JWT_ALGORITHM
from municipality_verification.verification import (
    get_pending_users, approve_user, reject_user
)
from municipality_verification.municipality_tools.municipality_approval_logger import (
    log_approval
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

municipality_verify_bp = Blueprint(
    "municipality_verify",
    __name__,
    template_folder="templates"
)


@municipality_verify_bp.route("/", methods=["GET"])
def show_verify():
    """
    GET /staff/verify
    - 承認待ちユーザー一覧を HTML でレンダリング (staff_verify.html)
    - テストではこちらは使わず、POST のみ検証する
    """
    users = get_pending_users()
    return render_template("staff_verify.html", users=users)


@municipality_verify_bp.route("/", methods=["POST"])
def do_verify():
    """
    POST /staff/verify
    - Authorization: Bearer <staff_jwt> を期待
    - フォームデータまたは JSON で {uuid, action} を受け取る
    - 承認 or 却下を実行し、ログを記録して結果メッセージを返す (テストでは本文に文字列含有を検証)
    """
    # 1) ヘッダーからトークンを取り出す
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return "トークンなし", 401

    # 2) JWT を検証
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        staff_id = decoded.get("staff_id")
        if not staff_id:
            return "JWT不正", 401
    except Exception as e:
        return f"JWTエラー: {e}", 401

    # 3) フォーム／JSON からデータを取得
    data = request.form.to_dict() if request.form else request.get_json(silent=True) or {}
    uuid_val  = data.get("uuid")
    action    = data.get("action")

    if not uuid_val or action not in ("approve", "reject"):
        return "uuid & action 必須", 400

    # 4) 承認／却下を実行
    if action == "approve":
        approve_user(uuid_val)
        message = f"ユーザー {uuid_val} を承認しました"
    else:
        reject_user(uuid_val)
        message = f"ユーザー {uuid_val} を却下しました"

    # 5) 承認ログを残す
    client_ip = request.remote_addr
    log_approval(uuid_val, action, approver_id=staff_id, client_ip=client_ip)

    # 6) 結果メッセージを返す
    return message
