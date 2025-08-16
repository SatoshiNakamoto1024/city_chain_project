# user_manager/profile/profile.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from flask import Blueprint, request, render_template, jsonify, redirect, url_for
import logging
from user_manager.user_manager import get_user, update_user
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import boto3
from user_manager.config import DYNAMODB_TABLE, AWS_REGION
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(DYNAMODB_TABLE)

profile_bp = Blueprint("profile_bp", __name__, template_folder="templates")

@profile_bp.route("/", methods=["GET", "POST"])
def profile():
    if request.method == "POST":
        uuid_val = request.form.get("uuid")
        if not uuid_val:
            return jsonify({"error": "uuid is required"}), 400
        update_data = dict(request.form)
        update_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        try:
            updated_user = update_user(uuid_val, update_data)
            return jsonify(updated_user.to_dict())
        except Exception as e:
            logger.error("プロフィール更新エラー: %s", e)
            return jsonify({"error": str(e)}), 500
    else:
        uuid_val = request.args.get("uuid")
        if not uuid_val:
            return jsonify({"error": "uuid parameter is required"}), 400
        user = get_user(uuid_val)
        if user:
            return render_template("profile.html", user=user.to_dict())
        else:
            return jsonify({"error": "User not found"}), 404