"""
Flask アプリ本体

* CORS はフロントを localhost から動かす前提で全許可
* Blueprint で JIS API と 登録 API を分離
"""
from __future__ import annotations

import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask
from flask_cors import CORS

from municipality_registration.api_jis_data import jis_api_bp
from municipality_registration.routes import municipality_reg_bp  # 登録用エンドポイント

# ---------------------------------------------------------------------------- #
def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # CORS: 本番は適切な Origin に絞る
    CORS(app, resources={
        r"/api/*":          {"origins": "*"},
        r"/municipality/*": {"origins": "*"},   # 追加
    })

    # Blueprint 登録
    app.register_blueprint(jis_api_bp)        # JIS データ API
    app.register_blueprint(municipality_reg_bp)  # 市町村登録 API / 画面

    return app


if __name__ == "__main__":
    # `python app_municipality_registration.py` で単体起動
    create_app().run(host="0.0.0.0", port=6050, debug=True)
