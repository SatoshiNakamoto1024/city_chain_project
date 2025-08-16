# login_app/routes/admin_routes.py
import os, sys, copy, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from flask import Blueprint, request, jsonify
from login_app.account_manager.register_account import register_account
from login_app.account_manager.login_account    import login_account
from login_app.decorators import require_role

admin_bp = Blueprint("admin_routes", __name__)

@admin_bp.post("/admin/register")
@require_role("admin")    # ← 既存のシステム管理者がさらに admin を発行する想定
def admin_register():
    data = request.get_json() or {}
    data["role"] = "admin"
    return jsonify(register_account(data))

@admin_bp.post("/admin/login")
def admin_login():
    data = request.get_json() or {}
    data["role"] = "admin"
    return jsonify(login_account(data))
