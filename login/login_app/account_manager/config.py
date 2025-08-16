# account_manager/config.py
import os

# ───────── AWS & テーブル ─────────
AWS_REGION         = os.getenv("AWS_REGION", "us-east-1")
MUNICIPALITY_TABLE = os.getenv("MUNICIPALITY_TABLE", "Municipalities")
STAFF_TABLE        = os.getenv("STAFF_TABLE",        "MunicipalStaffs")
ADMIN_TABLE        = os.getenv("ADMIN_TABLE",        "AdminsTable")
USERS_TABLE        = os.getenv("USERS_TABLE",        "UsersTable")

# ───────── JWT (管理者・自治体用) ─────────
JWT_SECRET    = os.getenv("MUNI_JWT_SECRET", "municipal_secret")
JWT_ALGORITHM = "HS256"
JWT_EXP_HOURS = 24

# ───────── JIS JSON の置き場所 ─────────
BASE_DIR   = os.path.abspath(os.path.dirname(__file__))
JIS_BASE   = os.path.join(BASE_DIR, "static", "jis")
# 同じフォルダ直下の region_tree.json を参照するようにします。
REGION_JSON = os.path.join(BASE_DIR, "region_tree.json")