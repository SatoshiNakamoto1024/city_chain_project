# login_app/app_login.py
"""
app_login.py  ― メインエントリポイント (フェーズ1+2＋送信DApps統合)
  * 住民登録 /device 認証  (既存)
  * 市町村職員 / システム管理者   ←★今回追加
  * 住民承認 UI / API            ←★今回追加
"""

import sys, os, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if os.name == "nt":                       # Windows だけ
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from flask_cors import CORS
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import jwt  # PyJWT を利用
from login_app.config import DEBUG, HOST, PORT, SECRET_KEY

# Blueprint imports
from login_app.register import register_bp
from auth_py.client_cert.certificate_info import cert_bp
from login_app.logout import logout_bp
from user_manager.app_user_manager import user_bp
from login_app.login_routes import login_bp   # ← NEW!
from user_manager.utils.app_utils import utils_bp
from user_manager.utils.login_handler import device_auth_bp
from routes.staff_routes         import staff_bp        # /staff/*
from routes.admin_routes         import admin_bp        # /admin/*
from municipality_verification.approval_api import approve_bp   # /staff/verify
from municipality_verification.views       import views_bp      # /staff/login など

# ① ここで送信DApps の Blueprint をインポート
#    パスはプロジェクト構成に合わせて調整してください
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from dapps.sending_dapps.sending_dapps import send_bp  # ← 追加

# 先頭付近で追加
# from infra.logging_setup import configure_logging
# configure_logging()               # ←たった 1 行で全コンポーネント有効

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(asctime)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = SECRET_KEY
    CORS(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    # 既存の Blueprint 登録
    app.register_blueprint(register_bp,  url_prefix="/register")
    app.register_blueprint(cert_bp,      url_prefix="/certificate")
    app.register_blueprint(logout_bp,    url_prefix="/logout")
    app.register_blueprint(user_bp,      url_prefix="/user")
    app.register_blueprint(utils_bp)          # → /utils/detect_platform, /utils/check_storage
    app.register_blueprint(device_auth_bp)    # → /device_auth/login
    app.register_blueprint(login_bp, url_prefix="/login")
    # ── 新規追加: 送信DApps 用エンドポイント ──
    app.register_blueprint(send_bp, url_prefix="/send")  # ← 追加
    # ------------- ★ 新 Blueprint -------------
    app.register_blueprint(staff_bp)          # /staff/register , /staff/login
    app.register_blueprint(admin_bp)          # /admin/register , /admin/login
    app.register_blueprint(approve_bp)        # /staff/verify (REST)
    app.register_blueprint(views_bp)          # /staff/login (HTML) /staff/verify_ui

    return app


if __name__ == "__main__":
    # 初回リクエストが 10 s 超え→ReadTimeout になりやすい。
    os.environ["PYTHONUTF8"] = "1"       #  これだけ
    create_app().run(host=HOST, port=PORT,
                     debug=DEBUG, use_reloader=False)
