import boto3
from botocore.exceptions import ClientError

# 使用する SNS トピック ARN（コンソールで確認できる）
TOPIC_ARN = 'arn:aws:sns:us-east-1:235494777820:DevNotificationTopic'  # ←自分のに差し替えて

# 使用するプロファイル名（例：dev-sso）
session = boto3.Session(profile_name="dev-sso", region_name="us-east-1")
sns = session.client("sns")

def send_test_notification():
    try:
        response = sns.publish(
            TopicArn=TOPIC_ARN,
            Message="テスト通知です。SNS の設定は正しく動作しています。",
            Subject="【テスト】SNS 通知"
        )
        print("✅ 通知送信成功！ MessageId:", response["MessageId"])
    except ClientError as e:
        print("❌ 通知送信失敗:", e.response["Error"]["Message"])

if __name__ == "__main__":
    send_test_notification()
