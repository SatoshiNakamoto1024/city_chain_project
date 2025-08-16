# login_app/routes/app_routes.py
import os, sys, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from flask import Blueprint, request, jsonify
from login_app.account_manager.app_account_manager import create_account, login

app_bp = Blueprint("app_routes", __name__)

@app_bp.post("/register")
def resident_register():
    """
    住民（resident）用の登録エンドポイント
    """
    data = request.get_json() or {}
    data["role"] = "resident"
    return jsonify(create_account(data))

@app_bp.post("/login")
def resident_login():
    """
    住民（resident）用のログインエンドポイント
    """
    data = request.get_json() or {}
    data["role"] = "resident"
    return jsonify(login(data))
