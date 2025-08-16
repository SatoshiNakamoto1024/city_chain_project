# login_app/certificate_info.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Blueprint, request, render_template, jsonify
import boto3
from login_app.config import AWS_REGION, USER_TABLE

cert_bp = Blueprint("cert_bp", __name__, template_folder="templates")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USER_TABLE)

@cert_bp.route("/info", methods=["GET"])
def show_certificate_info():
    """
    GET /certificate/info
      - ユーザー認証等により取得すべきですが、ここではシンプルにデータがあればテンプレートに渡す例。
    """
    # 例として、登録済みユーザーの中から最初の1件を選ぶ
    scan_resp = users_table.scan()
    items = scan_resp.get("Items", [])
    if not items:
        return "ユーザーが1件も登録されていません。", 400

    user_item = items[0]
    cert_info = user_item.get("certificate")
    if not cert_info:
        return "証明書情報がありません。", 400

    return render_template("certificate_info.html", cert=cert_info)
