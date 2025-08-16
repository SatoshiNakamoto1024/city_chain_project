import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
import boto3

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)  # すべてのエンドポイントに CORS ヘッダーを付与

# Blueprint のインポート（login_app 内の各pyファイル）
from registration import registration_bp
from login import login_bp
from profile import profile_bp
from lifeform import lifeform_bp

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object("login_app.config")

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')

# 各 Blueprint の登録
app.register_blueprint(registration_bp, url_prefix="/auth")
app.register_blueprint(login_bp, url_prefix="/auth")
app.register_blueprint(profile_bp, url_prefix="/user")
app.register_blueprint(lifeform_bp, url_prefix="/lifeform")

# 設定：S3 のバケット名やリージョン
app.config["AWS_REGION"] = "us-east-1"
app.config["S3_BUCKET"] = "my-dummy-bucket-2025"

# boto3 の S3 クライアントを作成（AWS CLI や環境変数で認証設定が必要）
s3 = boto3.client("s3", region_name=app.config["AWS_REGION"])

@app.route("/")
def index():
    # トップページ：シンプルな登録フォームへのリンクなどを表示
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # リクエストの Content-Type に応じてデータを取得
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # 登録日時を追加（UTC ISO 8601 形式）
        data["registered_at"] = datetime.utcnow().isoformat() + "Z"
        # ファイル名をメールアドレスと現在時刻で生成（メールがなければ "unknown"）
        email = data.get("email", "unknown")
        timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        filename = f"{email}_{timestamp_str}.json"

        try:
            s3.put_object(
                Bucket=app.config["S3_BUCKET"],
                Key=filename,
                Body=json.dumps(data, ensure_ascii=False, indent=4)
            )
            return jsonify({"success": True, "message": f"Data uploaded as {filename}"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return render_template("register.html")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
