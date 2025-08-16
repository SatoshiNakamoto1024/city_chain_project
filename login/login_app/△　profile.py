# login_app/profile.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Blueprint, request, render_template, jsonify
import logging
from user_manager.user_manager import get_user, update_user
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

profile_bp = Blueprint("profile", __name__, template_folder="templates")

@profile_bp.route("/", methods=["GET", "POST"])
def profile():
    if request.method == "POST":
        uuid_val = request.form.get("uuid")
        if not uuid_val:
            return jsonify({"error": "uuid is required"}), 400
        update_data = request.form.to_dict()
        try:
            update_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            updated_user = update_user(uuid_val, update_data)
            return jsonify(updated_user)
        except Exception as e:
            logger.error("プロフィール更新エラー: %s", e)
            return jsonify({"error": str(e)}), 500
    else:
        uuid_val = request.args.get("uuid")
        if not uuid_val:
            return jsonify({"error": "uuid parameter is required"}), 400
        user = get_user(uuid_val)
        if user:
            return render_template("profile.html", user=user)
        else:
            return jsonify({"error": "User not found"}), 404
