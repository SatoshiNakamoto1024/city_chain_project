# municipality_verification/app_municipality_verification.py

import sys
import os

# プロジェクトルートを import パスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, render_template, request, jsonify
import hmac
import hashlib
import jwt
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__, template_folder="templates")

# 全エンドポイントに対して CORS を許可する
CORS(app)

# 簡易的に JWT 用のシークレットをハードコーディング
# 実運用では環境変数や config.py を参照してください
JWT_SECRET           = "my_jwt_secret_2025"
JWT_ALGORITHM        = "HS256"
JWT_EXPIRATION_HOURS = 1


def hash_password(password: str, salt: str) -> str:
    """
    パスワードのハッシュを生成 (salt + password → SHA-256)
    """
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def generate_staff_jwt(staff_id: str) -> str:
    """
    staff_id をペイロードに含めた JWT を生成し返却
    """
    payload = {
        "staff_id": staff_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


###############
# 1) ログイン画面表示 (GET)
###############
@app.route("/staff/login", methods=["GET"])
def staff_login_page():
    """
    GET /staff/login : 市町村職員用ログインフォーム HTML を返す
    """
    return render_template("staff_login.html")


###############
# 2) ログインAPI (POST)
###############
@app.route("/staff/login", methods=["POST"])
def staff_login_api():
    """
    POST /staff/login : JSON または form データで {staff_id, password, municipality} を受け取り、
                         極めて簡易的にダミー検証（ID=staff001, PW=secret123）なら JWT を返す。
                         それ以外は 401 エラー。
    """
    data = request.get_json() or request.form.to_dict()
    staff_id     = data.get("staff_id")
    password     = data.get("password")
    municipality = data.get("municipality")  # 必要に応じて使う

    if not (staff_id and password and municipality):
        return jsonify({"success": False, "message": "staff_id, password, municipality が必須です"}), 400

    # 簡易ダミー検証: staff_id=staff001, password=secret123 ならログイン成功とみなす
    if staff_id == "staff001" and password == "secret123":
        token = generate_staff_jwt(staff_id)
        return jsonify({"success": True, "jwt": token})
    else:
        return jsonify({"success": False, "message": "ログイン失敗"}), 401


###############
# 3) 承認画面表示 (GET)
###############
@app.route("/staff/verify", methods=["GET"])
@app.route("/staff/verify/", methods=["GET"])
def staff_verify_html():
    """
    GET /staff/verify : 承認待ちユーザー一覧をダミーで表示する HTML を返す
    """
    # テスト用またはダミーUIとして、pendingユーザーのサンプルを返す
    users = [
        {"uuid": "user-111"},
        {"uuid": "user-222"},
    ]
    return render_template("staff_verify.html", users=users, message="", error="")


###############
# 4) 承認API (POST)
###############
@app.route("/staff/verify", methods=["POST"])
def staff_verify_api():
    """
    POST /staff/verify : Authorization ヘッダーで JWT を受け取り、
                          JSON または form データで {uuid, action} を受け取る。
                          ダミー検証として、action が "approve" の場合は
                          {"success": True, "message": "ユーザー <uuid> を承認"}、
                          action が "reject" の場合は
                          {"success": True, "message": "ユーザー <uuid> を却下"} を返す。
                          JWT が正しくない場合は 401、action が不正なら 400。
    """
    # 1) ヘッダーからトークンを取り出す
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"error": "トークンなし"}), 401

    # 2) JWT を検証して staff_id を取得
    try:
        decoded  = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        staff_id = decoded.get("staff_id")
        if not staff_id:
            return jsonify({"error": "JWT不正"}), 401
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "JWT期限切れ"}), 401
    except Exception as e:
        return jsonify({"error": f"JWTエラー: {e}"}), 401

    # 3) JSON もしくは form データから uuid と action を取得
    data     = request.get_json() if request.is_json else request.form.to_dict()
    uuid_val = data.get("uuid")
    action   = data.get("action")

    if not uuid_val or action not in ("approve", "reject"):
        return jsonify({"error": "uuid と action が必要"}), 400

    # 4) ダミーロジック: 実際の DB 更新は行わずメッセージだけ返す
    if action == "approve":
        return jsonify({"success": True, "message": f"ユーザー {uuid_val} を承認しました"}), 200
    else:
        return jsonify({"success": True, "message": f"ユーザー {uuid_val} を却下しました"}), 200


def create_app():
    """
    Flask アプリ生成用ファクトリ関数。
    Blueprint を利用する場合はここに登録する。
    """
    app = Flask(__name__, template_folder="templates")
    CORS(app)
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
