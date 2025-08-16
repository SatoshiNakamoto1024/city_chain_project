# admin/admin_auth.py
import os, jwt
from datetime import datetime, timezone
from flask import request, jsonify
from functools import wraps

ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", "super-admin-secret")
ADMIN_ROLE       = "admin"


def _decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, ADMIN_JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


def is_admin(req) -> dict | None:
    """Authorization: Bearer <token> から管理者権限を判定"""
    hdr = req.headers.get("Authorization", "")
    if not hdr.startswith("Bearer "):
        return None
    claims = _decode_token(hdr.split()[1])
    if not claims or claims.get("role") != ADMIN_ROLE:
        return None
    if claims.get("exp", 0) < datetime.now(timezone.utc).timestamp():
        return None
    return claims


def admin_required(fn):
    """Blueprint で使うデコレーター"""
    @wraps(fn)
    def _wrap(*a, **kw):
        if not is_admin(request):
            return jsonify({"error": "admin token required"}), 401
        return fn(*a, **kw)
    return _wrap
