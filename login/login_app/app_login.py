# login_app/app_login.py

import sys, os, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from flask_cors import CORS
from flask import Flask, render_template
from login_app.config import DEBUG, HOST, PORT, SECRET_KEY

# ────────── Blueprint imports ──────────
from login_app.register import register_bp
from auth_py.client_cert.certificate_info import cert_bp
from login_app.logout import logout_bp
from user_manager.app_user_manager import user_bp
from login_app.login_routes import login_bp
from user_manager.utils.app_utils import utils_bp
from user_manager.utils.login_handler import device_auth_bp
from routes.staff_routes import staff_bp
from routes.admin_routes import admin_bp
from municipality_verification.approval_api import approve_bp
from municipality_verification.views import municipality_verify_bp as views_bp

# ────────── 追加 Blueprint: マッピング管理 API ──────────
from mapping_continental_municipality.routes import mapping_bp

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
# from dapps.sending_dapps.sending_dapps import send_bp

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
    app.register_blueprint(utils_bp)
    app.register_blueprint(device_auth_bp)
    app.register_blueprint(login_bp,     url_prefix="/login")
    # app.register_blueprint(send_bp,      url_prefix="/send")
    app.register_blueprint(staff_bp)     # /staff/register, /staff/login
    app.register_blueprint(admin_bp)     # /admin/register, /admin/login
    app.register_blueprint(approve_bp)   # /staff/verify (JSON) & /staff/select_region/<uuid> & POST /staff/verify
    app.register_blueprint(views_bp)     # /staff/login (HTML), /staff/verify_ui

    # 【追加】マッピング一括管理 API
    app.register_blueprint(mapping_bp)      # /mapping/set_mapping, /mapping/get_users

    return app

if __name__ == "__main__":
    os.environ["PYTHONUTF8"] = "1"
    create_app().run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)
