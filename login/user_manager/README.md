以下は、ユーザー個人情報の管理、パスワード・鍵・マイナンバーなどの変更手続きや厳格な管理を行うために、
「user-manager」というフォルダー配下に各機能ごとに分割したサンプル実装例です。
※ 以下はダミー実装ですが、本番環境では各処理（バリデーション、DBアクセス、AWS連携など）をより堅牢に実装する必要があります。

12. ディレクトリ構成まとめ
arduino
Copy
Edit
user_manager/
├── __init__.py
├── app_user_manager.py          (メインテストスクリプト)
├── config.py
├── password_manager.py
├── user_validation.py
├── user_service.py
├── user_model.py
├── user_manager.py
├── user_db.py
├── profile/
│   ├── app_profile.py           (追加)
│   ├── profile.py
│   ├── profile_edit.py          (追加)
│   ├── profile_data/            (ローカル管理フォルダ)
├── lifeform/
│   ├── app_lifeform.py          (追加)
│   ├── lifeform.py
│   ├── lifeform_check.py        (追加)
│   ├── lifeform_data/           (ローカル管理フォルダ)
これで「ご提示の既存ファイル」はすべて修正し、
「存在しないものは追加」 してフル機能を揃えています。

使い方
python user_manager/app_user_manager.py を実行すると、
AWS環境変数に基づいて DynamoDB / S3 に接続
ユーザー新規登録 → ユーザー取得 → プロフィール更新 → パスワード変更 → 鍵更新 → 生命体登録を一連で行う
結果がログおよびコンソールに出力される
ローカルに lifeform_data/, profile_data/ などが作成され、
S3には "users/{user_uuid}.json" が保存され、
DynamoDB (UsersTable) に登録・更新されます。

拡張
もしFlask APIとして提供したい場合は、各 app_XXX.py（app_profile.py 等）をサーバーとして起動し、Blueprint登録します。user_manager.py での register_user_wrapper を使うこともできますが、ここではあまり使っていない例です。


補足説明
user_manager/config.py
では、ユーザー管理に関する設定（必須フィールド、パスワードの最低文字数、マイナンバーの桁数など）を定義します。

user_manager/user_model.py
は、ユーザーのデータモデルを dataclass で定義し、辞書／JSON への変換を行います。

user_manager/user_db.py
は、AWS の DynamoDB や S3 へのユーザー情報の保存・取得・更新処理を実装します。
※ ここでは、auth-py/config.py の設定を参照しているので、環境変数等で値を変更可能です。

user_manager/user_validation.py
は、メールアドレス、マイナンバー、パスワードなどの入力値の整合性検証を行います。

user_manager/user_service.py
は、登録・プロフィール更新・パスワード変更・鍵更新などの高レベルサービスを提供します。
ここでは、auth-py/registration.py の機能や auth-py/jwt_manager.py の JWT 発行も利用しています。

これらのファイルを組み合わせることで、ユーザー個人情報の厳格な管理や変更手続きが実装され、後続の DApps などに安全なユーザー情報を渡す基盤が構築できます。


boto3 が使用する認証情報を確認し、S3 にアクセスできるかテストする方法
1. AWS CLI で認証情報を確認
boto3 は、AWS CLI の認証情報を使用します。
まず、現在の認証情報が正しく設定されているか確認しましょう。

(1) 現在の認証情報を確認する
以下のコマンドを実行してください。

powershell
Copy
Edit
aws configure list
すると、以下のような結果が出ます。

pgsql
Copy
Edit
      Name                    Value             Type    Location
      ----                    -----             ----    --------
   profile                <not set>             None    None
access_key     ****************HNXB shared-credentials-file
secret_key     ****************aneK shared-credentials-file
    region                us-east-1      config-file    ~/.aws/config
✅ 確認するポイント

access_key と secret_key が設定されていること
region が us-east-1 になっていること（S3 バケットのリージョンに一致しているか）
2. AWS CLI で S3 バケットにアクセスできるか確認
boto3 も AWS CLI と同じ認証情報を使うので、AWS CLI で S3 にアクセスできるかテストします。

(1) S3 のバケット一覧を取得
powershell
Copy
Edit
aws s3 ls --profile s3testuser
→ もし S3 のバケットが一覧表示されれば、認証情報は正しく設定されています。

(2) 特定のバケット（my-resister-bucket-2025）をリスト表示
powershell
Copy
Edit
aws s3 ls s3://my-resister-bucket-2025 --profile s3testuser
→ このコマンドが成功すれば、少なくとも s3:ListBucket の権限はあるということ。

(3) S3 にテストファイルをアップロード
powershell
Copy
Edit
echo "Test File" > test.txt
aws s3 cp test.txt s3://my-resister-bucket-2025/test.txt --profile s3testuser
✅ 成功すれば、s3:PutObject の権限もある。
❌ 失敗（AccessDenied など）が出た場合は、IAM ポリシーの設定を見直す必要あり。

(4) アップロードしたファイルをダウンロード
powershell
Copy
Edit
aws s3 cp s3://my-resister-bucket-2025/test.txt downloaded_test.txt --profile s3testuser
✅ 成功すれば、s3:GetObject の権限もある。

3. boto3 で使用する認証情報を確認
boto3 が AWS CLI で設定した認証情報を正しく使っているか確認します。

(1) Python の boto3 で確認
Python 環境で、以下のコードを実行してください。

python
Copy
Edit
import boto3

session = boto3.Session()
credentials = session.get_credentials()
current_credentials = credentials.get_frozen_credentials()

print("Access Key:", current_credentials.access_key)
print("Secret Key:", current_credentials.secret_key)
print("Session Token:", current_credentials.token)  # これは一時認証の場合のみ
✅ 表示される Access Key と Secret Key が AWS CLI で設定したものと一致しているか確認してください。
❌ 一致しない場合は、boto3 が別の認証情報を参照している可能性があります。（環境変数や別の認証ファイルなど）

4. boto3 で S3 にアクセスできるか確認
次に、boto3 で S3 にアクセスできるかテストします。

(1) boto3 で S3 のバケット一覧を取得
Python 環境で、以下のコードを実行してください。

python
Copy
Edit
import boto3

s3 = boto3.client('s3')

try:
    response = s3.list_buckets()
    print("S3 バケット一覧:")
    for bucket in response['Buckets']:
        print(bucket['Name'])
except Exception as e:
    print("エラー:", e)
✅ 成功すれば、認証情報は正しく設定されている。
❌ 失敗（AccessDenied など）が出た場合は、IAM ポリシーや認証情報を見直す必要あり。

(2) boto3 で S3 にファイルをアップロード
python
Copy
Edit
import boto3

s3 = boto3.client('s3')

bucket_name = "my-resister-bucket-2025"
file_name = "test.txt"
key_name = "test_upload.txt"

try:
    s3.upload_file(file_name, bucket_name, key_name)
    print(f"アップロード成功: {file_name} → s3://{bucket_name}/{key_name}")
except Exception as e:
    print("エラー:", e)
✅ 成功すれば、boto3 でも s3:PutObject の権限がある。
❌ 失敗（AccessDenied など）が出た場合は、IAM ポリシーを再確認する。

5. IAM ポリシーの確認
上記のテストで AccessDenied が出た場合、IAM のポリシーが正しく設定されていない可能性が高いです。
AWS マネジメントコンソールで IAM に行き、s3testuser の アタッチされているポリシー を確認してください。

以下のポリシーが含まれているかチェックしてください。

必要なポリシー
json
Copy
Edit
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::my-resister-bucket-2025",
                "arn:aws:s3:::my-resister-bucket-2025/*"
            ]
        }
    ]
}
✅ これが IAM ユーザーに適用されていれば OK！
❌ ない場合は、IAM のポリシーを修正して再アタッチしてください。

6. もう一度 app_user_manager.py を実行
IAM ポリシーを修正した後、python app_user_manager.py をもう一度実行してください。

もし また AccessDenied のエラーが出たら、再度 aws s3 ls コマンドや boto3 のテストを試して、問題の原因を特定 してください。

まとめ
✅ AWS CLI で aws s3 ls や aws s3 cp を試す
✅ boto3 で list_buckets() や upload_file() を試す
✅ IAM ユーザーに適切なポリシーがあるか確認する
✅ バケットポリシーで拒否されていないか確認する

この流れで原因を特定すれば、app_user_manager.py での AccessDenied エラーが解決できます！


#　dilithium5 を埋め込んだので、python312でのサーバー起動は下記から
# まずはpython312に各種インストール
作業	具体例
3.12のPython.exeを確認	（なければインストール）
D:\Python\Python312\python.exe -m venv D:\city_chain_project\.venv312
作ったあと、
D:\city_chain_project\.venv312\Scripts\activate.bat
という具合に、仮想にはいること。

D:\Python\Python312\python.exe -m pip install flask flask-cors requests boto3 qrcode pytest PyJWT cryptography pillow qrcode[pil]

これにより、Python 3.12 環境でテストが実行され、既にインストール済みの Pillow（PIL）が利用されるはずです。


# この login_handler.py は「テスト専用の簡易API」として整えた版です。
app_utils.py は本番で「本物のエンドポイント」を作るときに使う

login_handler.py はテストにおいて /login をシンプルにチェックする用途

テストコード (test_utils.py) も「100MBあればログインOK！」という挙動を検証できるようになります。

これで「単に100MBあればログインできる」という要件をシンプルに満たし、test_utils.py と整合も取れるはずです。

collected 2 items

test_utils.py::TestLoginHandler::test_login_pc_ok PASSED                                                                   [ 50%]
test_utils.py::TestLoginHandler::test_login_android_ok PASSED                                                              [100%] 

======================================================= warnings summary ======================================================== 
test_utils.py::TestLoginHandler::test_login_pc_ok
  D:\Python\Python314\Lib\site-packages\pytest_asyncio\plugin.py:1190: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================================= 2 passed, 1 warning in 7.03s ================================================== 
