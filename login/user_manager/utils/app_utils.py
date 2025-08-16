# File: user_manager/utils/app_utils.py

from flask import Blueprint, request, jsonify
import logging
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from user_manager.utils.platform_utils import detect_platform_from_headers
from user_manager.utils.storage_checker   import check_storage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Blueprint 定義。URLプレフィックスは /utils
utils_bp = Blueprint("utils_bp", __name__, url_prefix="/utils")

@utils_bp.route("/detect_platform", methods=["GET"])
def platform_detect():
    """
    GET /utils/detect_platform
    User-Agent や X-Device-Type ヘッダからプラットフォーム種別を判定して返す。
    """
    platform = detect_platform_from_headers(request.headers)
    return jsonify({"platform_type": platform})

@utils_bp.route("/check_storage", methods=["GET"])
def storage_check():
    """
    GET /utils/check_storage
    1) User-Agent から端末種別を判定  
    2) check_storage(platform_type) を呼び出して 100MB 以上あるか判定  
    """
    platform = detect_platform_from_headers(request.headers)
    ok = check_storage(platform)

    status  = 200 if ok else 403
    message = "Storage OK (100MB+)" if ok else "Insufficient storage (<100MB) or error"
    return jsonify({
        "platform_type": platform,
        "storage_ok": ok,
        "message": message
    }), status
