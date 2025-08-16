# registration/email_sender.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import boto3
import logging
from registration.config import AWS_REGION, SNS_TOPIC_ARN
from registration.qr_util import generate_qr_s3_url

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sns_client = boto3.client("sns", region_name=AWS_REGION)

def send_registration_notification(username: str, email: str, user_uuid: str):
    certificate_url = f"http://192.168.3.8:5000/certificate/info?uuid={user_uuid}"
    # QRコード画像のS3アップロード → 公開URLを取得
    qr_url = generate_qr_s3_url(certificate_url, user_uuid)

    message = (
        f"[登録通知] ユーザー {username} ({email}) が登録されました。\n"
        f"UUID: {user_uuid}\n"
        f"証明書確認ページ: {certificate_url}\n"
        f"QRコード画像リンク:\n{qr_url}\n"
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
