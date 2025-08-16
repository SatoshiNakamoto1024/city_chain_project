# registration/app_registration.py
import os
import sys
import logging
from flask import Flask

# 親ディレクトリ (login) を sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register_user_interface(registration_data: dict) -> dict:
    """
    アプリケーション層のユーザー登録インターフェース関数。
    他モジュールが直接 registration.registration を参照するのを避け、
    この関数経由で登録処理を利用できるようにします。
    """
    from registration.registration import register_user as _register_user
    return _register_user(registration_data)


def get_certificate_interface(uuid: str) -> dict:
    """
    クライアント証明書メタデータ取得用インターフェース。
    uuid に紐づく証明書情報を返します。
    """
    # auth_py.client_cert モジュールの get_certificate_info を利用
    from auth_py.client_cert.client_cert import get_certificate_info
    cert_info = get_certificate_info(uuid)
    if not cert_info:
        raise Exception(f"Certificate not found for uuid={uuid}")
    return cert_info


def create_app():
    # テンプレートフォルダの絶対パスを指定
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
    app = Flask(__name__, template_folder=template_path)
    
    # registration_bp を import して Blueprint 登録
    from registration.routes import registration_bp
    app.register_blueprint(registration_bp, url_prefix="/register")
    
    # デバッグ用：登録されたルート一覧を出力
    with app.app_context():
        logger.info("=== Flask Routes ===")
        for rule in app.url_map.iter_rules():
            logger.info(rule)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
