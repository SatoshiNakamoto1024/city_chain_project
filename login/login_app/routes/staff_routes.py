# login_app/routes/staff_routes.py
import os, sys, copy, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Blueprint, request, jsonify
from account_manager.register_account import register_account
from account_manager.login_account    import login_account

staff_bp = Blueprint("staff_routes", __name__)

@staff_bp.post("/staff/register")
def staff_register():
    data = request.get_json() or {}
    data["role"] = "staff"
    return jsonify(register_account(data))

@staff_bp.post("/staff/login")
def staff_login():
    data = request.get_json() or {}
    data["role"] = "staff"
    return jsonify(login_account(data))
