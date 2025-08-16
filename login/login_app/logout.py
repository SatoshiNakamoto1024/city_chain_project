# login_app/logout.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Blueprint, render_template

logout_bp = Blueprint("logout_bp", __name__, template_folder="templates")

@logout_bp.route("/", methods=["GET"])
def logout():
    """
    GET /logout
    実際にはJWTの削除(クライアント側)などだが、ここではテンプレート表示だけ。
    """
    return render_template("logout.html")
