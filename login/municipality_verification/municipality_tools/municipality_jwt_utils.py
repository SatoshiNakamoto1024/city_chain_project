# municipality_verification/municipality_tools/municipality_jwt_utils.py

import os
import logging
import jwt

# 環境変数から JWT に関する設定を取得
JWT_SECRET    = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def verify_staff_jwt(token: str) -> str | None:
    """
    staff（市町村職員）用 JWT トークンを検証し、payload 内の "staff_id" を返す。
    - 有効期限切れや不正な署名の場合は None を返す。
    """
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded.get("staff_id")
    except jwt.ExpiredSignatureError:
        logger.warning("JWT 期限切れ")
        return None
    except Exception as e:
        logger.error("JWT 検証失敗: %s", e)
        return None
