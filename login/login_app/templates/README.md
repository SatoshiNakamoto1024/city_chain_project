また、S3にアップロードする前提 で、適切に HTML, JavaScript, URL遷移処理 を組み込みます。

# 4. 環境変数の設定
テストを実行する前に、AWS の認証情報とリージョンを環境変数に設定します。たとえば、Windows の場合は以下のようにします：

set AWS_ACCESS_KEY_ID=あなたのアクセスキーID
set AWS_SECRET_ACCESS_KEY=あなたのシークレットアクセスキー
set AWS_DEFAULT_REGION=us-east-1

# AWS CLI の設定を利用する
すでにAWS CLIをインストールしている場合、以下のコマンドを実行して認証情報を設定できます。
aws configure
ここで、アクセスキーID、シークレットアクセスキー、デフォルトリージョン（例: ap-southeast-2）、出力形式（json など）を入力してください。

# 認証情報ファイルを利用する
通常、AWS CLIで設定すると、~/.aws/credentials に認証情報が保存されます。boto3はこのファイルからも認証情報を読み込むため、環境変数の設定がなくても、正しく設定されていれば動作します。

# Step 6: S3にファイルをアップロード
aws s3 cp D:\test-file.txt s3://my-resister-bucket-2025/

# AWS 環境を確認
PS D:\city_chain_project\login\login_app> aws s3 ls
>> 下記があればOK
2025-03-16 14:58:30 my-resister-bucket-2025

PS D:\city_chain_project\login\login_app> aws sts get-caller-identity
{
    "UserId": "AIDATNVEVEPOEWNXFBFSM",
    "Account": "235494777820",
    "Arn": "arn:aws:iam::235494777820:user/s3testuser"
}

まず、ローカルのテスト用ファイル test_upload.txt を作成して、それを citychainprojectsend バケットにアップロードしてみます。
✅ コマンド（アップロード）
echo "This is a test file for S3 upload." > test_upload.txt
aws s3 cp test_upload.txt s3://my-resister-bucket-2025/test_upload.txt

3. S3からファイルをダウンロード
アップロードしたファイルをローカルにダウンロードして、内容が正しいか確認します。
✅ コマンド（ダウンロード）
aws s3 cp s3://my-resister-bucket-2025/test_upload.txt test_download.txt

4. ダウンロードしたファイルの内容を確認
ダウンロードした test_download.txt の内容を確認します。
✅ コマンド（表示）
type test_download.txt
✔ This is a test file for S3 upload. が表示されればOK！

echo "This is a test file for S3 upload." > test_upload.txt
>> aws s3 cp test_upload.txt s3://my-resister-bucket-2025/test_upload.txt
upload: .\test_upload.txt to s3://my-resister-bucket-2025/test_upload.txt
PS D:\city_chain_project\login\login_app> aws s3 cp s3://my-resister-bucket-2025/test_upload.txt test_download.txt
download: s3://my-resister-bucket-2025/test_upload.txt to .\test_download.txt
PS D:\city_chain_project\login\login_app> type test_download.txt

# s3://my-resister-bucket-2025 バケットにファイルをアップロード
PS D:\city_chain_project\login\login_app> cd templates
PS D:\city_chain_project\login\login_app\templates> aws s3 cp index.html s3://my-resister-bucket-2025/index.html
upload: .\index.html to s3://my-resister-bucket-2025/index.html 
PS D:\city_chain_project\login\login_app\templates> aws s3 cp lifeform.html s3://my-resister-bucket-2025/lifeform.html
upload: .\lifeform.html to s3://my-resister-bucket-2025/lifeform.html
PS D:\city_chain_project\login\login_app\templates> aws s3 cp login.html s3://my-resister-bucket-2025/login.html
upload: .\login.html to s3://my-resister-bucket-2025/login.html
PS D:\city_chain_project\login\login_app\templates> aws s3 cp municipality_verify.html s3://my-resister-bucket-2025/municipality_verify.html
upload: .\municipality_verify.html to s3://my-resister-bucket-2025/municipality_verify.html
PS D:\city_chain_project\login\login_app\templates> aws s3 cp profile.html s3://my-resister-bucket-2025/profile.html
upload: .\profile.html to s3://my-resister-bucket-2025/profile.html
PS D:\city_chain_project\login\login_app\templates> aws s3 cp register.html s3://my-resister-bucket-2025/register.html
upload: .\register.html to s3://my-resister-bucket-2025/register.html
PS D:\city_chain_project\login\login_app\templates> 

新しいコードが反映されず、前のバージョンが表示される原因として、いくつかの可能性が考えられます。以下を確認してください：
ブラウザが古いバージョンをキャッシュしている可能性があります。
ハードリロード（Ctrl+F5、またはCmd+Shift+R）やシークレットモードで再確認してください。

# Blueprint の登録が必要
Blueprint は、Flask アプリケーションの機能をモジュール単位で整理するための仕組みです。個々の Blueprint に、関連するルート、テンプレート、静的ファイルなどをまとめることで、大規模なアプリケーションを分割して管理しやすくなります。たとえば、ユーザー認証や生命体管理などの機能ごとに Blueprint を作成し、メインの Flask アプリに登録することで、コードの再利用や分割統治が可能になります。
コードには、Blueprint を利用して lifeform 関連のルートを別ファイル（lifeform.py）にまとめ、app_s3.py でそれを登録する例です。
※ここでは、app_s3.py の全体コードを修正後の全文として示します。lifeform.py も同じディレクトリまたはパッケージ内に配置してある前提です。

# Blueprint の役割
Blueprint はアプリケーションの機能をモジュール化するための仕組みです。
例えば、ログイン機能用、登録機能用、プロフィール管理用といった具合に、それぞれを独立した Blueprint として定義し、それをメインの Flask アプリに登録することで、コードの整理や再利用が容易になります。
✅ 単一サーバーで複数の Blueprint を運用可能
1 つの Flask アプリケーション（例えば、app_s3.py）で、複数の Blueprint を登録すれば、各機能ごとのルートを一つのサーバーで提供できます。
たとえば、/login, /register, /profile といった URL に対応する各 Blueprint を設定しておけば、ユーザーはこれらのエンドポイントにアクセスできます。
✅ URL プレフィックスの利用
Blueprint を登録する際に URL プレフィックスを設定すれば、例えば app.register_blueprint(login_bp, url_prefix="/login") のようにすることで、ログイン関連のルートはすべて /login 以下にまとめられます。
同様に、登録機能やプロフィール機能も個別にプレフィックスを設定することで整理できます。
✅ まとめると：
各 HTML ページごとに別々の Flask アプリケーションを立ち上げる必要はなく、1 つの Flask アプリケーション内に複数の Blueprint を定義し、すべての機能を 1 つのサーバー（例: python app_s3.py）で運用するのが一般的な方法です。


🌟 目標
index.html（トップページ）
「ログイン」ボタン → login.html へ遷移
「新規登録」ボタン → register.html へ遷移
登録完了後、「プロフィール管理」「生命体管理」ボタンを追加表示
（登録後のリロード時に localStorage を利用）

register.html（新規登録ページ）
登録フォームを入力し、「登録」ボタンを押すとデータをS3へ送信
登録完了後、index.html に遷移してボタンが追加
「戻る」ボタン → index.html に戻る
登録ボタンを押すと、ユーザー情報は JSON 形式で AWS S3 に保存されます。具体的には、auth_py/registration.py の中で、以下の処理が行われています：
ユーザー情報をまとめた user_record という辞書が作成される
S3 クライアント（boto3.client("s3", region_name=AWS_REGION)）を使って、
バケット名は config.py で設定されている S3_BUCKET（例："my-resister-bucket-2025"）に、
キーは "user_registration/{user_uuid}.json" の形式で保存されます。
つまり、実際の保存先は S3 バケットの中の "user_registration" フォルダ（プレフィックス）で、ファイル名はユーザーごとの UUID に基づいた JSON ファイルです。

login.html（ログインページ）
ユーザーIDとパスワードを入力し、「ログイン」ボタンを押す
認証成功時 → index.html に戻り、プロフィール/生命体管理ボタンが追加される
「戻る」ボタン → index.html に戻る

profile.html（プロフィール管理ページ）
プロフィールを管理できるページ
「戻る」ボタン → index.html に戻る

lifeform.html（生命体管理ページ）
生命体情報を登録・管理できるページ
「戻る」ボタン → index.html に戻る

# app_s3.py で実行テスト
もともと Flask アプリケーションは、app = Flask(__name__) のように定義されたアプリケーションインスタンスを持ちます。

このインスタンスには、すべてのルーティング、設定、ミドルウェアなどが含まれており、これを使ってリクエストを処理します。
もし既存のアプリ（app.py）が複雑でエラーが出る場合、単純なテスト用のファイル（app_s3.py）を作成し、その中でシンプルなアプリケーションインスタンスを定義・実行することで、必要な機能（今回はS3アップロードのみ）だけをテストできます。
そのため、別ファイルでアプリケーションインスタンスを定義しておけば、他のモジュールに依存せずに動作させることができます。
このように、不要な依存関係を排除したシンプルなエントリーポイント（app_s3.py）を作ることで、S3連携のテストをまずは独立して行うことが可能です。

新たに app_s3.py を作成して、S3へのアップロードのみをテストする
その際、既存の複雑な依存関係は使わず、シンプルな Flask アプリとして構築する
AWS認証情報は事前に設定しておくこと
これで、S3の登録ボタンを押すとJSONファイルがS3に保存される動作をテストできるはずです。

次に確認すべきこと
S3バケットの中身の確認
AWSコンソールで該当バケットを開き、指定されたファイル名（例："kibiyakko@gmail.com_20250315085930.json"）が存在することを確認してください。

データ内容の確認
アップロードされたJSONファイルを開いて、入力したデータが正しく保存されているかチェックします。

エラーハンドリングの強化
今回は基本的なテストに成功しましたが、今後はさらに詳細なエラーチェックやログ出力の追加も検討すると良いでしょう。


# 証明書情報画面（/certificate/info）
→ こちらは、ユーザーが後から自分の登録時に発行された証明書の詳細（シリアル番号、フィンガープリント、証明書の有効期間など）を確認できるようにするためのページです。
→ ユーザーはログイン後、必要に応じて証明書の内容を確認でき、ダウンロードリンクやQRコード（もしあれば）も表示される場合があります。

# QRコード
→ こちらは、主に通知（たとえばSNS通知やメール）でユーザーに提供されるものです。
→ QRコードは、証明書のダウンロードリンクや証明書確認ページへのURLを短く、かつ視覚的に提供するために使われます。
→ ユーザーはスマホなどでQRコードを読み取ることで、簡単に証明書情報にアクセスできるようになります。