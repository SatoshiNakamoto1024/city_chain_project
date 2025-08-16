# login/app.py

from flask import Flask, request, jsonify
from registration.app_registration import registration_bp
from auth.app_auth import auth_bp
from user_manager.app_user import user_bp
from CA.app_ca import ca_bp
from login.config import HOST, PORT, DEBUG, JWT_SECRET
import logging
from flask_cors import CORS
import asyncio

# sending_dapps モジュールをインポート
from sending_dapps.sending_dapps import process_sending_transaction

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def create_app():
    """
    Flaskアプリを生成し、各Blueprintを登録して返す。
    """
    app = Flask(__name__, template_folder="templates")

    # CORSを全エンドポイントで許可
    CORS(app)

    # 各 Blueprint 登録
    app.register_blueprint(registration_bp, url_prefix="/registration")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(ca_bp, url_prefix="/ca")

    @app.route("/")
    def index():
        return (
            "<h1>CityChain トップページ</h1>"
            "<p>"
            "<a href='/registration'>ユーザー登録</a> | "
            "<a href='/auth/login'>ログイン</a> | "
            "<a href='/ca/info'>証明書確認</a> | "
            "<a href='/dapps/send'>送金DApps</a>"
            "</p>"
        )

    # 新エンドポイント: sending_dapps の呼び出し
    @app.route("/dapps/send", methods=["GET", "POST"])
    def dapps_send():
        """
        GET -> サンプルHTMLを返す(フォームなど)
        POST -> sending_dapps.process_sending_transaction(...) を呼び出してDAGへ送る
        """
        if request.method == "GET":
            return (
                "<h2>Sending DApps - Send Screen</h2>"
                "<form method='POST' action='/dapps/send'>"
                "Sender: <input name='sender'><br>"
                "Receiver: <input name='receiver'><br>"
                "Message: <input name='message'><br>"
                "<button type='submit'>Send</button>"
                "</form>"
            )
        else:
            # POST
            # Content-TypeがJSONの場合とformの場合を考慮
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()

            # JWTトークンは通常Authorizationヘッダーから
            jwt_token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if not jwt_token:
                # デモのため、dummyを使う
                jwt_token = "dummy_jwt_token"

            try:
                # sending_dappsは非同期処理なので asyncio.run(...) で呼び出し
                result = asyncio.run(process_sending_transaction(data, jwt_token))
                return jsonify(result), 200
            except Exception as e:
                logger.error("DApps送信エラー: %s", e)
                return jsonify({"error": str(e)}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    logger.info("Starting login app on port=%d, debug=%s", PORT, DEBUG)
    app.run(host=HOST, port=PORT, debug=DEBUG)
