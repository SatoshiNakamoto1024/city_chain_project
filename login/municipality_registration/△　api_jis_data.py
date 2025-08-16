# municipality_registration/api_jis_data.py
import os, sys, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Blueprint, jsonify
from municipality_registration.config import JIS_BASE

jis_api_bp = Blueprint("jis_api", __name__, url_prefix="/api/jis")

@jis_api_bp.get("/continents")
def get_continents():
    """
    大陸コード（文字列配列）を返す
    """
    path = os.path.join(JIS_BASE, "continents.json")
    return jsonify(json.load(open(path, encoding="utf-8")))

@jis_api_bp.get("/countries")
def get_countries():
    """
    全ての国コード＋大陸情報を返す
    """
    path = os.path.join(JIS_BASE, "countries.json")
    return jsonify(json.load(open(path, encoding="utf-8")))

@jis_api_bp.get("/prefectures")
def get_prefectures():
    """
    日本の都道府県リストを返す
    """
    path = os.path.join(JIS_BASE, "prefectures_jp.json")
    return jsonify(json.load(open(path, encoding="utf-8")))

@jis_api_bp.get("/municipalities/<pref_code>")
def get_municipalities(pref_code):
    """
    指定都道府県(pref_code)の市町村リストを返す
    """
    path = os.path.join(JIS_BASE, f"municipalities_{pref_code}.json")
    if not os.path.exists(path):
        return jsonify([])
    return jsonify(json.load(open(path, encoding="utf-8")))
