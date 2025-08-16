# registration/email_sender.py

import boto3
import logging
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from registration.config import AWS_REGION, SNS_TOPIC_ARN
from registration.qr_util import generate_qr_base64  # 追加（共通QR生成関数）

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sns_client = boto3.client("sns", region_name=AWS_REGION)

def send_registration_notification(username: str, email: str, user_uuid: str):
    certificate_url = f"http://localhost:5000/certificate/info?uuid={user_uuid}"
    qr_data_url = generate_qr_base64(certificate_url)

    message = (
        f"[登録通知] ユーザー {username} ({email}) が登録されました。\n"
        f"UUID: {user_uuid}\n"
        f"証明書確認ページ: {certificate_url}\n"
        f"QRコード（画像を右クリックして保存可能）:\n{qr_data_url}\n"
    )

    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject="【通知】ユーザー登録完了"
        )
        logger.info("SNS通知送信完了: %s", user_uuid)
    except Exception as e:
        logger.error("SNS通知エラー: %s", e)
        raise