# login/wallet/app_wallet.py
# -*- coding: utf-8 -*-
"""
app_wallet.py

1) ユーティリティ-モード
   python app_wallet.py <user_uuid>
       ↳ ウォレットを生成（または取得）して残高を +100 して表示

2) サーバー-モード
   python app_wallet.py --serve [--port 5050]
       ↳ /wallet/... エンドポイントだけの極小 Flask サーバーを起動し、
          ブラウザや curl で手動テストが可能
"""

import sys
import os
import logging

# プロジェクトルート (login/) を import パスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from wallet.wallet_service import (
    create_wallet_for_user,
    increment_balance,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(asctime)s %(message)s",
)

USAGE = """
Usage:
  python app_wallet.py <user_uuid>
  python app_wallet.py --serve [--port PORT]
"""

def run_utility_mode(user_uuid: str) -> None:
    """CLI から UUID を受け取り簡易動作確認を行う"""
    w = create_wallet_for_user(user_uuid)
    logging.info("Wallet obtained: %s", w.to_json())
    new_bal = increment_balance(w.wallet_address, 100.0)
    logging.info("After +100 → balance = %.2f", new_bal)

def run_server_mode(port: int = 5050) -> None:
    """/wallet Blueprint だけを載せた簡易 Flask サーバーを起動"""
    from flask import Flask
    from wallet.wallet_routes import wallet_bp

    app = Flask(__name__)
    app.register_blueprint(wallet_bp)

    logging.info("  Wallet API server running on http://0.0.0.0:%d/", port)
    # デバッグは True 固定（本ユーティリティ専用なので）
    app.run(host="0.0.0.0", port=port, debug=True)

# ─────────────────────────────
# メインエントリ
# ─────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(USAGE.strip())
        sys.exit(0)

    # サーバーモード
    if sys.argv[1] == "--serve":
        # デフォルト 5050 / 任意指定可
        port = 5050
        if "--port" in sys.argv:
            try:
                port_idx = sys.argv.index("--port") + 1
                port = int(sys.argv[port_idx])
            except (IndexError, ValueError):
                logging.error("--port の指定が不正です")
                sys.exit(1)
        run_server_mode(port)
        sys.exit(0)

    # ユーティリティ-モード
    user_uuid = sys.argv[1]
    run_utility_mode(user_uuid)
