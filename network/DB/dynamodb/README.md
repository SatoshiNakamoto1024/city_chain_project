✅ 1. AWS クレデンシャルとは？
AWS クレデンシャルとは、あなたのプログラムが AWS のリソースにアクセスするための 認証情報 です。大きく分けて次の2つの方法があります：
方法	    使用場面	      特徴
IAMロール	EC2やLambdaなど本番環境	  セキュリティが高く自動的に管理
アクセスキー&シークレットキー	ローカルPCの開発環境	自分で管理が必要（漏洩注意）

✅ 2. ローカル開発環境での設定（あなたのPC）
✅ ステップ1: AWS CLI をインストール（まだなら）
pip install awscli

✅ ステップ2: AWS CLI でクレデンシャルを設定
aws configure
すると、次のようなプロンプトが出ます：
AWS Access Key ID [None]:  例）AKIAxxxxxxxxxxxxxxx
AWS Secret Access Key [None]: xxxxxxxxxxxxxxxxxxxxxxxx
Default region name [None]: ap-northeast-1  ← 東京リージョンならこれ
Default output format [None]: json

✅ 裏で保存される場所：
~/.aws/credentials にクレデンシャル情報

~/.aws/config にリージョン情報

✅ 確認方法
aws sts get-caller-identity
成功すれば、現在の IAM ユーザーやロール情報が出てきます。

✅ 3. 本番環境での設定（EC2, Lambdaなど）
本番環境では「IAM ロール」を使います。
たとえば EC2 インスタンス上で Flask を動かしているなら、以下の手順で IAM ロールを使います。

✅ ステップ1: IAMロールを作成
AWS マネジメントコンソールにログイン

IAM → ロール → 「ロールを作成」

「信頼されたエンティティ」→ EC2

「アクセス権限ポリシー」→ 次のようなものを選択：

AmazonDynamoDBFullAccess

AmazonS3FullAccess

AmazonSNSFullAccess
※セキュリティを高めるために 必要最小限のポリシー にするのがベストです。

名前をつけて作成（例：my-app-role）

✅ ステップ2: EC2 インスタンスに IAM ロールを割り当て
EC2 → 対象のインスタンス → アクション → セキュリティ → IAMロールの変更

作成した my-app-role を選択して保存

✅ ステップ3: boto3 側では 何も設定不要
IAM ロールを使っている EC2 や Lambda は、自動的に boto3 や AWS CLI がクレデンシャルを使えます。

✅ 4. Flask アプリ内での boto3 利用イメージ
import boto3

# region_name は config で指定
dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
sns = boto3.client("sns", region_name="ap-northeast-1")
s3 = boto3.client("s3", region_name="ap-northeast-1")
✅ 上記は ローカルでも本番でも共通コード
（boto3 は「どこから実行されているか」に応じて、自動的に適切なクレデンシャルを探してくれます）

✅ 5. SNS_TOPIC_ARN などは環境変数で管理
環境に応じて変えるもの（SNS トピックARN、DynamoDBテーブル名など）は .env や config.py で切り替えるようにしておくとベストです。

例（config.py）
import os

AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-1")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "dummy")  # テスト中は "dummy"
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "your_table_name")

✅ よくあるエラーと対処法
エラー内容	原因	対策
InvalidClientTokenId	認証情報が無効	正しいアクセスキーか、IAMロールが付与されているか確認
AccessDeniedException	ポリシー不足	IAMポリシーに必要な権限（DynamoDB/S3/SNS）を追加
botocore.exceptions.NoCredentialsError	クレデンシャルが見つからない	aws configure 実行 or IAMロールの設定確認

✅ まとめ
環境	 方法	  設定方法
ローカルPC	 アクセスキー	 aws configure で設定
本番（EC2）	 IAMロール	 EC2 にロールを付けるだけ
Flask側	    boto3が自動認識	    特別なコードは不要


# test_sns_publish.py
✅ 解決手順
① 再認証（SSO）を行う
aws sso login --profile dev-sso
これを実行すると、ブラウザが開いて AWS アクセスポータルにログインを求められます。
正しくログインすれば、トークンが再発行されます。

# 実行結果
② トークン再発行後、再度、SNSのテストコードを実行
python test_sns_publish.py
これでエラーは消え、SNS に通知が送られるはずです。

PS D:\city_chain_project\network\DB\dynamodb> aws sso login --profile dev-sso
>>
Attempting to automatically open the SSO authorization page in your default browser.
If the browser does not open or you wish to use a different device to authorize this request, open the following URL:

https://oidc.us-east-1.amazonaws.com/authorize?response_type=code&client_id=talZLySVYgj361Y2ynGFfnVzLWVhc3QtMQ&redirect_uri=http%3A%2F%2F127.0.0.1%3A55088%2Foauth%2Fcallback&state=23f72d2f-a7d9-43fe-ab05-af6860a59aed&code_challenge_method=S256&scopes=sso%3Aaccount%3Aaccess&code_challenge=ZkAZOn61mq9YPhUqILgIeRAT519eh6PDf709IaEYAck
Successfully logged into Start URL: https://d-9067cd4c98.awsapps.com/start
PS D:\city_chain_project\network\DB\dynamodb> python test_sns_publish.py
>>
✅ 通知送信成功！ MessageId: 136337d3-788b-55da-942a-57b05c59815b
PS D:\city_chain_project\network\DB\dynamodb> 


# Test_boto3.py
✅【ステップ 1】SatoshiNakamoto1024 に開発者権限を与える
➤ 対象：AWS IAM Identity Center (旧 AWS SSO)
AWS マネジメントコンソールにログイン

[IAM Identity Center] → [ユーザー] → SatoshiNakamoto1024] を選択

[グループ] または [ポリシーの割り当て] → 「権限セットの割り当て」

新規権限セットを作成（または既存を使う）

🛠 作るべき「権限セット」の例：
名前：DeveloperAccess

内容：

AmazonDynamoDBFullAccess

AmazonS3FullAccess

AmazonSNSFullAccess

必要に応じて CloudWatchLogsFullAccess や IAMReadOnlyAccess なども追加できます。

作成後、SatoshiNakamoto1024 にこの権限セットを割り当てる

✅【ステップ 2】AWS CLI から Identity Center にログイン設定
このユーザーは AWS CLI にログインする必要があります（Root ではなく）。
aws configure sso

対話形式で入力：
SSO Start URL → AWS Identity Center のURL（例：https://yourdomain.awsapps.com/start）

SSO Region → us-east-1 など

SSO Username → SatoshiNakamoto1024

Account → 開発に使う AWS アカウントID を選択

Role → 割り当てた DeveloperAccess を選択

CLI profile name → satoshi-dev など任意の名前

✅ ログイン後、自動的に ~/.aws/config に sso_session プロファイルが作成されます。

✅【ステップ 3】boto3 テストコードを Identity Center 向けに修正
Identity Center では boto3.Session(profile_name=...) を使用して、認証済みのプロファイルを読み込みます。

🔧 修正したテストコード（test_boto3.py）
import boto3
from botocore.exceptions import BotoCoreError, ClientError

PROFILE_NAME = "satoshi-dev"  # aws configure sso で登録したプロファイル名
REGION_NAME = "us-east-1"

DYNAMODB_TABLE_NAME = "UsersTable"
S3_BUCKET_NAME = "my-client-cert-bucket"
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:xxxxxxxxxxxx:YourSNSTopic"  # ←実際の ARN に置換

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
✅【ステップ 4】テスト実行

python test_boto3.py
実行前に aws sso login --profile satoshi-dev を行う必要があります！

🔐 補足
ポイント	内容
IAM Identity Centerユーザー	管理されているユーザー（メールアドレス単位でログイン）
アクセス権限の割当	Identity Center → アカウント → ユーザーに対して権限セット割当
aws configure sso	開発者PCから AWS にログインするためのコマンド
boto3 のプロファイル名	Session(profile_name="satoshi-dev") などとして呼び出す必要あり

PS D:\city_chain_project\login\auth_py> aws configure sso   
>>
SSO session name (Recommended): satoshi-dev
SSO start URL [None]: https://d-9067cd4c98.awsapps.com/star 
t
SSO region [None]: us-east-1
SSO registration scopes [sso:account:access]:
Attempting to automatically open the SSO authorization page in your default browser.
If the browser does not open or you wish to use a different device to authorize this request, open the following URL:

https://oidc.us-east-1.amazonaws.com/authorize?response_type=code&client_id=XxFxwHZiRKIBeiQS-Kds8nVzLWVhc3QtMQ&redirect_uri=http%3A%2F%2F127.0.0.1%3A55316%2Foauth%2Fcallback&state=915e3696-bc97-4e2a-a971-53410e3a62a0&code_challenge_method=S256&scopes=sso%3Aaccount%3Aaccess&code_challenge=dCd40H50fPzKLwXPSV9fXZnYx24KDBJTyBqTL-oUT2o
The only AWS account available to you is: 235494777820
Using the account ID 235494777820
There are 2 roles available to you.
Using the role name "DeveloperAccess"
Default client Region [us-east-1]: us-east-1
CLI default output format (json if not specified) [json]: json
Profile name [DeveloperAccess-235494777820]: satoshi-dev
To use this profile, specify the profile name using --profile, as shown:

aws sts get-caller-identity --profile satoshi-dev
PS D:\city_chain_project\network\DB\dynamodb> 

# テスト実行結果
PS D:\city_chain_project\network\DB\dynamodb> python test_boto3.py
[✓] セッション作成成功 (profile: satoshi-dev)

[✓] DynamoDB接続成功: UsersTable
    キー構成: [{'AttributeName': 'uuid', 'KeyType': 'HASH'}, {'AttributeName': 'session_id', 'KeyType': 'RANGE'}]
[✓] S3接続成功: my-client-cert-bucket
    → client_cert/6bc5796f-5a26-4e42-806d-6df2793ba4aa_20250328215608.json
    → test.txt
    → user_client_cert/test.txt
[✓] SNS接続成功: arn:aws:sns:us-east-1:235494777820:DevNotificationTopic
    属性: {'Policy': '{"Version":"2008-10-17","Id":"__default_policy_ID","Statement":[{"Sid":"__default_statement_ID","Effect":"Allow","Principal":{"AWS":"*"},"Action":["SNS:GetTopicAttributes","SNS:SetTopicAttributes","SNS:AddPermission","SNS:RemovePermission","SNS:DeleteTopic","SNS:Subscribe","SNS:ListSubscriptionsByTopic","SNS:Publish"],"Resource":"arn:aws:sns:us-east-1:235494777820:DevNotificationTopic","Condition":{"StringEquals":{"AWS:SourceOwner":"235494777820"}}}]}', 'Owner': '235494777820', 'SubscriptionsPending': '0', 'TopicArn': 'arn:aws:sns:us-east-1:235494777820:DevNotificationTopic', 'TracingConfig': 'PassThrough', 'EffectiveDeliveryPolicy': '{"http":{"defaultHealthyRetryPolicy":{"minDelayTarget":20,"maxDelayTarget":20,"numRetries":3,"numMaxDelayRetries":0,"numNoDelayRetries":0,"numMinDelayRetries":0,"backoffFunction":"linear"},"disableSubscriptionOverrides":false,"defaultRequestPolicy":{"headerContentType":"text/plain; charset=UTF-8"}}}', 'SubscriptionsConfirmed': '1', 'DisplayName': 'DevNotificationTopic', 'SubscriptionsDeleted': '0'}
PS D:\city_chain_project\network\DB\dynamodb> 


# test_dynamodb_crud.py
✅ 2. DynamoDB の CRUD テスト
🔧 前提：
UsersTable という DynamoDB テーブルが存在している

パーティションキー（uuid）とソートキー（session_id）がある

# 実行結果
PS D:\city_chain_project\network\DB\dynamodb> python test_dynamodb_crud.py
D:\city_chain_project\network\DB\dynamodb\test_dynamodb_crud.py:16: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  "created_at": datetime.utcnow().isoformat() + "Z"
✅ 登録完了 (uuid: 2098f462-d045-4279-bfeb-6664d4fda431)
🔍 取得成功: {'uuid': '2098f462-d045-4279-bfeb-6664d4fda431', 'username': 'test_user', 'created_at': '2025-03-30T11:09:43.782348Z', 'email': 'test@example.com', 'session_id': 'TEST'}
🛠️ 更新完了
🔍 取得成功: {'uuid': '2098f462-d045-4279-bfeb-6664d4fda431', 'username': 'updated_user', 'created_at': '2025-03-30T11:09:43.782348Z', 'email': 'test@example.com', 'session_id': 'TEST'}
🗑️ 削除完了
PS D:\city_chain_project\network\DB\dynamodb> 