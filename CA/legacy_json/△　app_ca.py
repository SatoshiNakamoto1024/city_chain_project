import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import base64
from datetime import datetime
from flask import Flask, request, jsonify, render_template
import boto3
import glob

from CA.cert_issuer import issue_certificate
from CA.ca_manager import revoke_certificate, list_certificates
from CA.config import LOCAL_CERT_STORAGE, LOCAL_METADATA_STORAGE, AWS_REGION, S3_BUCKET, DYNAMODB_TABLE

# ローカル保存先の設定（CA 管理用）
LOCAL_CERT_STORAGE = os.getenv("LOCAL_CERT_STORAGE", r"D:\city_chain_project\CA\certs")
LOCAL_METADATA_STORAGE = os.getenv("LOCAL_METADATA_STORAGE", r"D:\city_chain_project\CA\metadata")

# AWS 設定（本番環境用）
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "my-ca-bucket-2025")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "CACertificates")

app = Flask(__name__, template_folder="templates", static_folder="static")

s3 = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

os.makedirs(LOCAL_CERT_STORAGE, exist_ok=True)
os.makedirs(LOCAL_METADATA_STORAGE, exist_ok=True)

def generate_certificate_interface(uuid_val: str, validity_days: int = 365) -> tuple[bytes, str]:
    """
    インターフェース関数として、証明書発行処理を呼び出します。
    issue_certificate を内部で呼び出し、その結果を返します。
    """
    return issue_certificate(uuid_val, validity_days)


@app.route('/issue_cert', methods=['GET'])
def issue_cert():
    """
    GET パラメータ "uuid"（必須）および任意の "validity_days" を受け取り、  
    CA 用の証明書を発行する。発行した証明書は S3、DynamoDB、ローカルに保存する。
    レスポンスとして、Base64 化した証明書データとフィンガープリントを返す。
    """
    uuid_val = request.args.get("uuid")
    validity_days = request.args.get("validity_days", default=365, type=int)
    if not uuid_val:
        return jsonify({"error": "uuid parameter is required"}), 400
    try:
        cert_bytes, fingerprint = issue_certificate(uuid_val, validity_days)
        cert_data = json.loads(cert_bytes.decode("utf-8"))
        cert_data["fingerprint"] = fingerprint
        
        timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        s3_key = f"ca_cert/{uuid_val}_{timestamp_str}.json"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(cert_data, ensure_ascii=False, indent=4),
            ContentType="application/json"
        )
        
        db_item = {
            "uuid": uuid_val,
            "session_id": "CLIENT_CERT",
            "fingerprint": fingerprint,
            "valid_from": cert_data.get("valid_from"),
            "valid_to": cert_data.get("valid_to"),
            "revoked": cert_data.get("revoked"),
            "s3_key": s3_key,
            "issued_at": datetime.utcnow().isoformat() + "Z"
        }
        table.put_item(Item=db_item)
        
        local_metadata_filename = os.path.join(LOCAL_METADATA_STORAGE, f"{uuid_val}_{timestamp_str}.json")
        with open(local_metadata_filename, "w", encoding="utf-8") as f:
            json.dump(db_item, f, ensure_ascii=False, indent=4)
        local_cert_filename = os.path.join(LOCAL_CERT_STORAGE, f"{uuid_val}_{timestamp_str}.json")
        with open(local_cert_filename, "w", encoding="utf-8") as f:
            json.dump(cert_data, f, ensure_ascii=False, indent=4)
        
        cert_base64 = base64.b64encode(cert_bytes).decode("utf-8")
        return jsonify({
            "uuid": uuid_val,
            "client_cert": cert_base64,
            "fingerprint": fingerprint
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/revoke_cert', methods=['POST'])
def revoke_cert_endpoint():
    """
    POST リクエストの JSON ボディに "uuid" を含む場合、  
    証明書の失効処理を実施する（DynamoDB, S3, ローカルファイルの更新）。
    """
    data = request.get_json()
    if not data or "uuid" not in data:
        return jsonify({"error": "uuid is required in JSON body"}), 400
    uuid_val = data["uuid"]
    try:
        result = revoke_certificate(uuid_val)
        # ローカルファイル更新： uuid で始まるファイルを対象に更新
        for directory in [LOCAL_METADATA_STORAGE, LOCAL_CERT_STORAGE]:
            files = glob.glob(os.path.join(directory, f"{uuid_val}_*.json"))
            for fpath in files:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = json.load(f)
                content["revoked"] = True
                content["revoked_at"] = result["revoked_at"]
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(content, f, ensure_ascii=False, indent=4)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/list_cert', methods=['GET'])
def list_cert():
    """
    DynamoDB から全証明書メタデータを取得し、一覧として返す。
    """
    try:
        items = list_certificates()
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----- 開発用の CA 管理画面 (Web UI) を表示するエンドポイント -----  
@app.route('/client_cert_ui', methods=['GET'])
def client_cert_ui():
    """
    開発用：CA 管理画面（Web UI）を返します。
    この画面では、発行済み証明書の一覧や状態確認、失効操作などをブラウザで確認できます。
    ※本番環境では、この画面を公開しないようにしてください。
    """
    return render_template("client_cert.html")

if __name__ == '__main__':
    app.run(debug=True, port=6001)
