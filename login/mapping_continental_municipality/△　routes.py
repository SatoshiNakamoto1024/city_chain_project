# mapping_continental_municipality/routes.py
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Blueprint, request, jsonify
from mapping_continental_municipality.services import set_user_location_mapping, get_users_by_location

# Blueprint を "mapping_bp" という名前で定義し、URL プレフィックスを "/mapping" にする
mapping_bp = Blueprint("mapping_bp", __name__, url_prefix="/mapping")


@mapping_bp.route("/set_mapping", methods=["POST"])
def api_set_mapping():
    """
    POST /mapping/set_mapping

    リクエスト JSON ボディ:
        {
          "uuid":         "ユーザーUUID",
          "continent":    "Asia",
          "country":      "JP",
          "prefecture":   "13",
          "municipality": "Chiyoda"
        }

    レスポンス JSON:
      成功時: { "success": true }
      失敗時: { "success": false, "error": "エラーメッセージ" }
    """
    data = request.get_json(silent=True) or {}
    uuid_val     = data.get("uuid")
    continent    = data.get("continent")
    country      = data.get("country")
    prefecture   = data.get("prefecture")
    municipality = data.get("municipality")

    if not (uuid_val and continent and country and prefecture and municipality):
        return jsonify({"success": False, "error": "不足するフィールドがあります"}), 400

    try:
        set_user_location_mapping(uuid_val, continent, country, prefecture, municipality)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mapping_bp.route("/get_users", methods=["GET"])
def api_get_users():
    """
    GET /mapping/get_users

    クエリパラメータ:
      - continent (必須)
      - country    (オプション)
      - prefecture (オプション)
      - municipality (オプション)

    例:
      /mapping/get_users?continent=Asia
      /mapping/get_users?continent=Asia&country=JP
      /mapping/get_users?continent=Asia&country=JP&prefecture=13
      /mapping/get_users?continent=Asia&country=JP&prefecture=13&municipality=Chiyoda

    レスポンス JSON (成功時):
      [
        {
          "continent":    "Asia",
          "country":      "JP",
          "prefecture":   "13",
          "municipality": "Chiyoda",
          "uuid":         "user-1a2b3c4d"
        },
        …
      ]
    失敗時: { "error": "エラーメッセージ" }
    """
    continent   = request.args.get("continent")
    country     = request.args.get("country")
    prefecture  = request.args.get("prefecture")
    municipality = request.args.get("municipality")

    if not continent:
        return jsonify({"error": "continent is required"}), 400

    try:
        users = get_users_by_location(continent, country, prefecture, municipality)
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
