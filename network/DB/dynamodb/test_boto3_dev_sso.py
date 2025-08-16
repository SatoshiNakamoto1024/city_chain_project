# test_boto3_dev_sso.py

import boto3
from botocore.exceptions import BotoCoreError, ClientError

def main():
    try:
        # プロファイル名は dev-sso を使用
        session = boto3.Session(profile_name='dev-sso')
        sts = session.client("sts")
        identity = sts.get_caller_identity()

        print("✅ 認証成功！現在のユーザー情報:")
        print(f"👤 UserId:  {identity['UserId']}")
        print(f"🏢 Account: {identity['Account']}")
        print(f"🔗 ARN:     {identity['Arn']}")

    except (BotoCoreError, ClientError) as e:
        print("❌ 認証エラーまたは boto3 エラー:")
        print(e)

if __name__ == "__main__":
    main()
