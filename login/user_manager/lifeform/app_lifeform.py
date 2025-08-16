#!/usr/bin/env python
"""
app_lifeform.py

生命体( lifeform ) 登録を行う Flaskアプリ。
localhost:5000/lifeform で以下の処理を提供:

GET /lifeform
    -> 生命体登録フォーム (lifeform.html) を返す

POST /lifeform
    -> フォームまたは JSON データから受け取り、register_lifeform() にて生命体情報を登録
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import logging
import uuid
from datetime import datetime
from flask import Flask, Blueprint, request, jsonify, render_template

from user_manager.user_service import register_lifeform

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

lifeform_bp = Blueprint("lifeform_bp", __name__, template_folder="templates")

@lifeform_bp.route("/", methods=["GET", "POST"])
def lifeform_index():
    """
    GET -> lifeform.html を返す
    POST -> 生命体登録
    """
    if request.method == "POST":
        # フォーム or JSON
        if request.content_type and request.content_type.startswith("application/json"):
            data = request.get_json() or {}
        else:
            form_data = request.form.to_dict()
            extra_dims_str = form_data.get("extra_dimensions", "[]")
            try:
                extra_dims = json.loads(extra_dims_str)
            except:
                extra_dims = []
            data = {
                "user_id": form_data.get("user_id", "dummy"),
                "team_name": form_data.get("team_name", "UnknownTeam"),
                "affiliation": form_data.get("affiliation", "UnknownAffiliation"),
                "municipality": form_data.get("municipality", "UnknownCity"),
                "state": form_data.get("state", "UnknownState"),
                "country": form_data.get("country", "UnknownCountry"),
                "extra_dimensions": extra_dims
            }

        try:
            result = register_lifeform(data)
            return jsonify(result), 200
        except Exception as e:
            logger.error("生命体登録エラー: %s", e)
            return jsonify({"error": str(e)}), 500
    else:
        # GET
        return render_template("lifeform.html")

def create_app():
    """
    lifeform_bp を登録した Flaskアプリを生成し、返す。
    """
    app = Flask(__name__)
    app.register_blueprint(lifeform_bp, url_prefix="/lifeform")
    return app

if __name__ == "__main__":
    """
    python app_lifeform.py で直接起動する場合
    """
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
