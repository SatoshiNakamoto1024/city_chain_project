# municipality_registration/api_jis_data.py
"""
JIS（＋各国拡張）コードデータを返す簡易 API

Data 例:
  jis_data/
      continents.json
      countries.json
      prefectures_JP.json
      prefectures_FR.json
      municipalities_JP_18.json
      municipalities_FR_IDF.json
"""
from __future__ import annotations

import os
import sys
import json
from typing import Any, List

from flask import Blueprint, jsonify, abort

# プロジェクトルートを import パスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from municipality_registration.config import JIS_BASE  # noqa: E402

jis_api_bp = Blueprint("jis_api", __name__, url_prefix="/api/jis")


# ---------- ヘルパ ---------- #
def _load_json(fname: str) -> List[Any] | dict[str, Any]:
    path = os.path.join(JIS_BASE, fname)
    if not os.path.exists(path):
        abort(404, f"{fname} not found")
    with open(path, encoding="utf-8") as fp:
        return json.load(fp)


# ---------- ルート ---------- #
@jis_api_bp.get("/continents")
def get_continents():
    """大陸リスト（単純配列）"""
    return jsonify(_load_json("continents.json"))


@jis_api_bp.get("/countries")
def get_countries():
    """全世界の国リスト（大陸情報付き）"""
    return jsonify(_load_json("countries.json"))


@jis_api_bp.get("/prefectures/<country_code>")
def get_prefectures(country_code: str):
    """
    国コード別の都道府県／州リスト
    例: /api/jis/prefectures/JP → prefectures_JP.json
    """
    fname = f"prefectures_{country_code.upper()}.json"
    return jsonify(_load_json(fname))


@jis_api_bp.get("/municipalities/<country_code>_<pref_code>")
def get_municipalities(country_code: str, pref_code: str):
    """
    都道府県コード別の市町村リスト
    例: /api/jis/municipalities/JP_18 → municipalities_JP_18.json
    """
    fname = f"municipalities_{country_code.upper()}_{pref_code}.json"
    return jsonify(_load_json(fname))
