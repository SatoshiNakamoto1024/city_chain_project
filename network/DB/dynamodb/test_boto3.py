# test_boto3.py
import boto3
from botocore.exceptions import BotoCoreError, ClientError

PROFILE_NAME = "satoshi-dev"  # aws configure sso で登録したプロファイル名
REGION_NAME = "us-east-1"

DYNAMODB_TABLE_NAME = "UsersTable"
S3_BUCKET_NAME = "my-client-cert-bucket"
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:235494777820:DevNotificationTopic"  # ←実際の ARN に置換

def test_dynamodb(session):
    try:
        dynamodb = session.resource("dynamodb", region_name=REGION_NAME)
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        print(f"[✓] DynamoDB接続成功: {DYNAMODB_TABLE_NAME}")
        print("    キー構成:", table.key_schema)
    except Exception as e:
        print(f"[✗] DynamoDB接続失敗: {e}")

def test_s3(session):
    try:
        s3 = session.client("s3", region_name=REGION_NAME)
        res = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, MaxKeys=5)
        print(f"[✓] S3接続成功: {S3_BUCKET_NAME}")
        for obj in res.get("Contents", []):
            print("    →", obj["Key"])
    except Exception as e:
        print(f"[✗] S3接続失敗: {e}")

def test_sns(session):
    try:
        sns = session.client("sns", region_name=REGION_NAME)
        res = sns.get_topic_attributes(TopicArn=SNS_TOPIC_ARN)
        print(f"[✓] SNS接続成功: {SNS_TOPIC_ARN}")
        print("    属性:", res["Attributes"])
    except Exception as e:
        print(f"[✗] SNS接続失敗: {e}")

def main():
    try:
        session = boto3.Session(profile_name=PROFILE_NAME)
        print(f"[✓] セッション作成成功 (profile: {PROFILE_NAME})\n")
    except Exception as e:
        print(f"[✗] セッション作成失敗: {e}")
        return

    test_dynamodb(session)
    test_s3(session)
    test_sns(session)

if __name__ == "__main__":
    main()
