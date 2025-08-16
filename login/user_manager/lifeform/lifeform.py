import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
import json
import logging
from datetime import datetime
from flask import Blueprint, request, render_template, jsonify
import boto3
import jwt
from login_app.config import JWT_SECRET, S3_BUCKET, AWS_REGION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

lifeform_bp = Blueprint("lifeform", __name__, template_folder="templates")

S3_FOLDER = "user_lifeform"
LOCAL_SAVE_PATH = r"D:\city_chain_project\login\login_data\user_lifeform"
os.makedirs(LOCAL_SAVE_PATH, exist_ok=True)
s3_client = boto3.client("s3", region_name=AWS_REGION)

def verify_jwt(token):
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return decoded["uuid"]
    except Exception as e:
        logger.error("JWT検証エラー: %s", e)
        return None

@lifeform_bp.route("/", methods=["GET", "POST"])
def lifeform():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    uuid_from_jwt = verify_jwt(token)
    if not uuid_from_jwt:
        return jsonify({"error": "JWTが無効または期限切れです"}), 401

    if request.method == "POST":
        form_data = request.form.to_dict()
        final_dimensions_str = form_data.get("final_dimensions")
        if not final_dimensions_str:
            return jsonify({"error": "最終次元情報が送信されていません"}), 400
        try:
            final_dimensions = json.loads(final_dimensions_str)
        except Exception as e:
            return jsonify({"error": f"最終次元情報の解析に失敗しました: {e}"}), 400

        lifeform_id = form_data.get("lifeform_id", str(uuid.uuid4()))
        lifeform_data = {
            "uuid": uuid_from_jwt,
            "lifeform_id": lifeform_id,
            "dimensions": final_dimensions,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        # S3へ保存
        timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        filename = f"{uuid_from_jwt}_{timestamp_str}.json"
        s3_key = f"{S3_FOLDER}/{filename}"
        try:
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=json.dumps(lifeform_data, ensure_ascii=False, indent=4),
                ContentType="application/json"
            )
        except Exception as e:
            logger.error("S3保存失敗: %s", e)
            return jsonify({"error": f"S3保存失敗: {e}"}), 500

        # ローカル保存
        local_filepath = os.path.join(LOCAL_SAVE_PATH, filename)
        try:
            with open(local_filepath, "w", encoding="utf-8") as f:
                json.dump(lifeform_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error("ローカル保存失敗: %s", e)
            return jsonify({"error": f"ローカル保存失敗: {e}"}), 500

        return jsonify({
            "message": "生命体情報が登録されました",
            "lifeform_id": lifeform_id,
            "dimensions": final_dimensions
        })

    else:
        return render_template("lifeform.html", uuid=uuid_from_jwt)
