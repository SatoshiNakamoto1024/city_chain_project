# app_registration.py
import os
import sys
import logging
from flask import Flask
from boto3.dynamodb.conditions import Key

# ──────────────
# 親ディレクトリ (login) を sys.path に追加
# ──────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from infra.logging_setup import configure_logging
# configure_logging()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register_user_interface(registration_data: dict) -> dict:
    """
    新規ユーザー登録インターフェース。
    """
    from registration.registration import register_user as _register_user
    return _register_user(registration_data)


def get_certificate_interface(uuid: str) -> dict:
    """
    クライアント証明書メタデータ取得インターフェース。
    """
    from registration.registration import get_certificate_info as _get_cert_
    return _get_cert_(uuid)


def generate_qr_s3_url_interface(data: str, uuid: str) -> str:
    """
    QRコード生成（S3公開URL）インターフェース。
    registration/qr_util.py の generate_qr_s3_url をラップ
    """
    from registration.qr_util import generate_qr_s3_url as _gen_qr_
    return _gen_qr_(data, uuid)


def create_app():
    # テンプレートフォルダの絶対パスを指定
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
    app = Flask(__name__, template_folder=template_path)

    # Blueprint 登録
    from registration.routes import registration_bp
    app.register_blueprint(registration_bp, url_prefix="/registration")
    from registration.routes import auth_bp
    app.register_blueprint(auth_bp)

    # ルート一覧ログ出力
    with app.app_context():
        logger.info("=== Flask Routes ===")
        for rule in app.url_map.iter_rules():
            logger.info(rule)

    return app


# ───────────────────────────
# ここを追加：モジュール読み込み時にも app を生成
# (flask run で FLASK_APP=registration.app_registration などとしたときに必要)
# ───────────────────────────
app = create_app()


if __name__ == "__main__":
    # 開発サーバ起動
    app.run(host="0.0.0.0", port=5000, debug=True)
