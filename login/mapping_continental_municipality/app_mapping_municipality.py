# mapping_continental_municipality/app_mapping_municipality.py
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask
from mapping_continental_municipality.routes import mapping_bp
from flask_cors import CORS
import os

def create_mapping_app():
    """
    Flask アプリファクトリ関数:
      - Blueprint mapping_bp を URL プレフィックス "/mapping" で登録
      - CORS を有効化
    """
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(mapping_bp)
    return app


if __name__ == "__main__":
    # 直接このファイルを実行した場合のエントリポイント
    port = int(os.getenv("MAPPING_PORT", 6060))
    app = create_mapping_app()
    app.run(host="0.0.0.0", port=port, debug=True)
