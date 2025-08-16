# municipality_registration/routes.py
import os, sys
from flask import Blueprint, request, render_template, jsonify
import json
import logging

# モジュールのルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from municipality_registration.service import register_municipality
from municipality_registration.config import REGION_JSON

municipality_reg_bp = Blueprint(
    "municipality_reg_bp",
    __name__,
    template_folder="templates"
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@municipality_reg_bp.get("/municipality/regions")
def get_regions():
    """
    region_tree.json をそのまま返す API。
    フロントから fetch で呼び出します。
    """
    with open(REGION_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@municipality_reg_bp.get("/municipality/register")
def muni_reg_page():
    """
    GET 市町村登録フォーム
    """
    return render_template("municipality_register.html")

@municipality_reg_bp.post("/municipality/register")
def muni_reg_api():
    """
    POST 市町村登録API
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    try:
        res = register_municipality(data)
        return jsonify(res), 200
    except Exception as e:
        logger.exception("municipality registration failed")
        return jsonify({"success": False, "error": str(e)}), 400
