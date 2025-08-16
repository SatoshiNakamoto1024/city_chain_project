device_manager/
├── __init__.py
├── app_device_manager.py
├── config.py              (必要に応じて)
├── device_model.py
├── device_db.py
├── device_service.py
├── concurrency_policy.py
└── test_device_manager.py

【2台目端末での登録フロー】
1. ユーザーがQRコードをスマホなどで読み取る
2. QRコードに含まれるのは「Base64化されたクライアント証明書JSON」
3. QRコード内容をdecode（Base64 -> JSONへ）
4. JSONから uuid, fingerprint, 有効期限 などを取り出す
5. DynamoDBに問い合わせて「正規の証明書か？」を確認
6. 正常なら DevicesTable にこの端末情報を登録

まとめ
新しいフォルダ device_manager/ を追加
DevicesTable (DynamoDB) で (user_uuid, device_id) をキーに端末を管理
端末登録 (2台目以降) → qr_code やなんらかの仕組みで register_device_for_user()
同時利用端末数が1の場合 → 既存端末を強制削除 or セッション連携し強制ログアウト
テスト → test_device_manager.py で app_device_manager.py をサブプロセス起動し、エンドポイントを実際に呼び出す統合テスト

質問への回答:

「まずは登録時の端末でクライアント証明」 → その通り

「2台目の端末でどうするか」 → 例えば1台目で表示したQRコードをスキャンし、/device/register にリクエストする

「同時ログイン被り」 → concurrency_policy.py などで**「古い端末を強制ログアウト」** などの実装

「どのフォルダを追加?」 → この例では device_manager/ フォルダを追加し、app_device_manager.py, device_model.py, device_db.py, device_service.py, concurrency_policy.py, + テスト用の test_device_manager.py を新規作成

これで複数台端末によるクライアント証明管理 + 同時利用制限(強制ログアウト) のサンプルを示せます。
必要に応じて既存の login.py や session_manager と連携し、本格的に「端末ごとにセッションを持つ」「実際のX.509証明書発行・検証」などを導入してください。


# 4. 統合イメージ
ユーザーがログイン ( login_app/login.py )
パスワードOK → 端末を register_device_for_user(user_uuid, qr_code, device_name)
concurrency_policy で他の端末をログアウト
JWT発行し返却
ユーザーがセッション作成 ( session_manager/app_session_manager.py )
create_session() で DynamoDBにsession記録
device_manager で端末も登録 (or 更新)
concurrency_policy で古い端末を停止
実際は、どちらで端末登録するか は設計次第です。
login.py に全部含める
session_service.py にまとめる
2重登録しないように注意

まとめ
login.py 修正 → ログイン成功時に device_manager を呼び出し端末登録 & 同時利用制限
session_manager/app_session_manager.py 修正 → セッション作成時にも同様の連携を可能に


✅ 現在の仕様と要件の整理
1️⃣ 登録情報
1台目
　→ UsersTable: uuid, session_id などの基本情報（device_idは不要）
　→ この端末は最初に登録される主端末（Primary）

2台目以降
　→ DevicesTable: uuid, device_id, device_name, registered_at など
　→ 同じユーザーの追加端末（Secondary）

2️⃣ 実装すべき制御
同時ログインポリシー（MAX_CONCURRENT_DEVICES=1）を満たすように制御

「先にログインしていた端末を残すか、強制的に切断するか」をユーザー側に選ばせる
例えば：
新しい端末からログインしようとしたら、「他端末がアクティブです。切り替えますか？」と表示
切り替え了承→既存端末をログアウト（force_logout）
否→ログイン拒否（409 Conflict）

🛠 これからの修正の方向性
主な修正ポイントは以下の5ファイルです：
ファイル名	修正内容
device_service.py	ログイン時にすでにアクティブな端末があるか確認し、強制切断する処理を入れる（もしくは拒否）
device_db.py	アクティブな端末を検索する関数を追加
concurrency_policy.py	ログイン前に端末数チェックし、ポリシーに応じてエラーか強制終了か分岐
app_device_manager.py	/register のエンドポイントでポリシーチェックの分岐を呼び出す
test_device_manager.py	新ポリシーの動作確認用テスト追加（強制切断あり/なし）

✅ 最終まとめ
項目	説明
今の force_logout の実装	新しく登録された端末（new_device_id）を無条件で残す
あなたの求める仕様	“ログイン済み”が先だった端末だけを残す（それが1台目でも2台目でもよい）
必要な修正	Device モデルに login_at 追加し、force_logout で最も早いログインを残す
テスト修正	time.sleep(1) 等で login_at をずらし、動作検証


====================================================== test session starts =======================================================
platform win32 -- Python 3.14.0a4, pytest-8.3.4, pluggy-1.5.0 -- D:\Python\Python314\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project\login\device_manager
plugins: asyncio-0.25.3
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collected 5 items

test_device_manager.py::TestDeviceManagerIntegration::test_register_device PASSED                                           [ 20%]
test_device_manager.py::TestDeviceManagerIntegration::test_list_device PASSED                                               [ 40%]
test_device_manager.py::TestDeviceManagerIntegration::test_unbind_device PASSED                                             [ 60%]
test_device_manager.py::TestDeviceManagerIntegration::test_force_logout PASSED                                              [ 80%]
test_device_manager.py::TestDeviceManagerIntegration::test_reject_and_allow_with_force PASSED                               [100%]

======================================================== warnings summary ======================================================== 
test_device_manager.py::TestDeviceManagerIntegration::test_register_device
  D:\Python\Python314\Lib\site-packages\pytest_asyncio\plugin.py:1190: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated and slated for removal in Python 3.16
    return asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================================= 5 passed, 1 warning in 31.42s ================================================== 
PS D:\city_chain_project\login\device_manager> 