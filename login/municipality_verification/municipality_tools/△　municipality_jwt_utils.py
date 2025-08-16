# municipality_verification/municipality_tools/municipality_jwt_utils.py

import os
import logging
import jwt

# テスト時に環境変数から読み込めるように変更
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def verify_staff_jwt(token: str) -> str | None:
    """
    管理者用 JWT を検証し、payload 内の "staff_id" を返す。
    - token: クライアントから渡された JWT 文字列
    - 期限切れや不正な署名の場合は None を返す
    """
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded.get("staff_id")
    except jwt.ExpiredSignatureError:
        logger.warning("JWT期限切れ")
        return None
    except Exception as e:
        logger.error("JWT検証失敗: %s", e)
        return None
