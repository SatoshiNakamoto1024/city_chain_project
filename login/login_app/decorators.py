# login_app/decorators.py
"""
JWT 認可デコレータ
"""
from __future__ import annotations
import sys, os, logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import functools, jwt
from flask import request, jsonify, g
from municipality_verification.config import JWT_SECRET, JWT_ALGORITHM

def require_role(*roles):
    roles = set(r.lower() for r in roles)
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            except Exception:
                return jsonify({"error": "invalid token"}), 401
            if payload.get("role") not in roles:
                return jsonify({"error": "forbidden"}), 403
            g.current_user_role = payload["role"]
            g.current_user_uuid = payload["uuid"]
            return fn(*a, **kw)
        return wrapper
    return deco
