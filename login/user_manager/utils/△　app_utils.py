# File: user_manager/utils/app_utils.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, request, jsonify
import logging

from utils.platform_utils import detect_platform_from_headers
from utils.storage_checker import check_storage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Flask(__name__)

@app.route("/utils/detect_platform", methods=["GET"])
def platform_detect():
    """
    GET /utils/detect_platform
    
    User-Agent や X-Device-Type ヘッダからプラットフォーム種別を判定し、
    JSON形式で返すテスト用API。
    例:
      $ curl http://localhost:5050/utils/detect_platform -H "User-Agent: Mozilla/5.0 (Linux; Android 10)"
      -> {"platform_type": "android"}
    """
    platform = detect_platform_from_headers(request.headers)
    return jsonify({"platform_type": platform})

@app.route("/utils/check_storage", methods=["GET"])
def storage_check():
    """
    GET /utils/check_storage
    
    1. User-Agent から端末種類を判定 (pc, android, ios, etc.)
    2. check_storage(platform_type) を呼び出し、
       100MB以上の空き容量があるかどうかをサーバー側で判断。
       ただしPC/iot はサーバー側のディスク使用量をチェックし、
       android/ios/game等は仮or別ロジックを組むなど柔軟に対応可能。
       
    ここではサンプル実装として、storage_checker.py 内の
    check_storage(platform_type) が返したbooleanを返すのみ。
    """
    platform = detect_platform_from_headers(request.headers)
    result = check_storage(platform)  # storage_checker.py 内の check_storage関数

    if result:
        return jsonify({
            "platform_type": platform,
            "storage_ok": True,
            "message": "Storage OK (100MB+)"
        }), 200
    else:
        return jsonify({
            "platform_type": platform,
            "storage_ok": False,
            "message": "Insufficient storage (<100MB) or error"
        }), 403

if __name__ == "__main__":
    # ローカル実行用
    # 本番でGunicornなどで起動する場合は WSGIとして読み込む。
    app.run(host="0.0.0.0", port=5050, debug=True)
