# municipality_verification/municipality_routes.py

"""
Municipality (テナント) 用の REST API ルーティング例
（例として証明書失効APIだけ実装）
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Blueprint, request, jsonify, g
from municipality_verification.municipality_revoke_cert import municipality_revoke_cert
from login_app.decorators import require_role

municipality_bp = Blueprint("municipality", __name__)

@municipality_bp.post("/revoke_cert")
@require_role
def revoke_cert_municipality():
    """
    POST /revoke_cert
    - require_municipality デコレータで JWT 検証済み、g.current_user が staff_id、g.current_user_tenant が municipality を持つ
    - JSON で {uuid: ..., tenant_id: ...} を受け取り、証明書を失効
    """
    data = request.get_json()
    return jsonify(
        municipality_revoke_cert(
            data["uuid"], 
            g.current_user, 
            g.current_user_tenant
        )
    )
