# municipality_verification/approval_api.py

import os
import sys
from flask import Blueprint, request, jsonify, g, render_template
from boto3.dynamodb.conditions import Key as DynamoKey
import jwt

# プロジェクトルートを sys.path に追加して、他モジュールをインポートできるようにする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mapping_continental_municipality.services import set_user_location_mapping
from login_app.decorators import require_role
from municipality_verification.verification import (
    get_pending_users, approve_user, reject_user
)
from municipality_verification.municipality_tools.municipality_approval_logger import (
    log_approval
)

approve_bp = Blueprint("approve_bp", __name__)


@approve_bp.get("/staff/verify")
@require_role("staff")
def list_pending():
    """
    承認待ちユーザー一覧を JSON で返す。
    """
    return jsonify(get_pending_users())


@approve_bp.get("/staff/select_region/<string:user_uuid>")
@require_role("staff")
def select_region_for_user(user_uuid):
    """
    承認対象ユーザー (uuid) に対して、「地域を選んで承認 or 却下」を行う画面を表示する。
    テンプレート: templates/staff_select_region.html
    """
    return render_template("staff_select_region.html", uuid=user_uuid)


@approve_bp.post("/staff/verify")
@require_role("staff")
def verify():
    """
    ユーザー承認/却下エンドポイント。
    フォームまたは JSON で以下を受け付ける:

      - uuid         : 承認対象ユーザーの UUID (必須)
      - action       : "approve" もしくは "reject" (必須)
      - (以下は action="approve" のとき必須)
        * continent   : 大陸 (String)
        * country     : 国コード (String)
        * prefecture  : 県コード (String)
        * municipality: 市町村名 (String)

    承認時 (action="approve"):
      1) UsersTable 上で approval_status を "approved" に更新
      2) mapping_continental_municipality.services.set_user_location_mapping(...) を呼び出し、
         UserLocationMapping テーブルにマッピングを保存（既存マッピングがあれば削除→新規登録）
      3) 承認ログ (MunicipalApprovalLogTable) に記録
      4) JSON レスポンスを返す

    却下時 (action="reject"):
      1) UsersTable 上で approval_status を "rejected" に更新
      2) 承認ログに「reject」として記録
      3) JSON レスポンスを返す
    """
    data = request.get_json(silent=True) or request.form
    uuid_val = data.get("uuid", "").strip()
    action   = data.get("action", "").strip().lower()

    if not uuid_val or action not in ("approve", "reject"):
        return jsonify({"error": "uuid & action(required: approve/reject)"}), 400

    staff_id = g.current_user_uuid  # 承認者の staff UUID

    if action == "approve":
        # 地域情報の必須チェック
        continent    = data.get("continent", "").strip()
        country      = data.get("country", "").strip()
        prefecture   = data.get("prefecture", "").strip()
        municipality = data.get("municipality", "").strip()

        if not (continent and country and prefecture and municipality):
            return jsonify({"error": "approve の場合、continent, country, prefecture, municipality が必要"}), 400

        # 1) ユーザーを approved に更新
        try:
            approve_user(uuid_val)
        except Exception as e:
            return jsonify({"error": f"ユーザー承認処理エラー: {str(e)}"}), 500

        # 2) マッピング保存（既存レコードがあれば削除してから新規登録される）
        try:
            set_user_location_mapping(
                uuid=uuid_val,
                continent=continent,
                country=country,
                prefecture=prefecture,
                municipality=municipality
            )
        except Exception as e:
            return jsonify({"error": f"地域マッピング保存エラー: {str(e)}"}), 500

        # 3) 承認ログ記録
        try:
            log_approval(
                uuid_val,
                action,
                approver_id=staff_id,
                reason=None,
                client_ip=request.remote_addr
            )
        except Exception:
            # ログ記録失敗でも承認自体は成功と見なす
            pass

        return jsonify({"success": True, "message": f"ユーザー {uuid_val} を承認してマッピングしました。"}), 200

    else:  # action == "reject"
        # 1) ユーザーを rejected に更新
        try:
            reject_user(uuid_val)
        except Exception as e:
            return jsonify({"error": f"ユーザー却下処理エラー: {str(e)}"}), 500

        # 2) 承認ログに「reject」を記録
        try:
            log_approval(
                uuid_val,
                action,
                approver_id=staff_id,
                reason=None,
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        return jsonify({"success": True, "message": f"ユーザー {uuid_val} を却下しました。"}), 200
