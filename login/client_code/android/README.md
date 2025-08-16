#　本体はD:\city_chain_project\android_studio\ にある。
D:\city_chain_project\login\client_code\android\　にあるのはコピーしたサンプルコードです

✅ 2. storage_check 通知のタイミングを最適化する提案と実装ポイント
タイミング	処理内容	対応ファイル・行動
Login 成功時	100MB 確保後に /user/storage_check 通知	LoginActivity.kt ですでに実装済み
MainActivity に移動した直後	状態確認用再通知（オプション）	MainActivity.kt で再通知も可能（任意）
Logout時	/user/storage_check にて 0バイト として通知	LogoutActivity.kt 上記の通り修正済み

✅ サーバー側 DynamoDB 例（StorageUsageTable）記録内容
user_uuid	timestamp	reserved_bytes
test-user-uuid	2025-04-13T08:20:01.123Z	104857600
test-user-uuid	2025-04-13T08:40:00.000Z	0

✅ まとめると...
LoginActivity.kt: 予約直後に即通知 → 完了済み

MainActivity.kt: オプションで再通知可能

LogoutActivity.kt: 解放後に「0バイト」として通知 → 上記で実装完了

本番では UUID やセッション ID を保存・共有して使うこと


# まずはTESt環境を整える
作業	具体例
3.12のPython.exeを確認	（なければインストール）
D:\Python\Python312\python.exe -m venv D:\city_chain_project\.venv312
作ったあと、
D:\city_chain_project\.venv312\Scripts\activate.bat
という具合に、仮想にはいること。

# TEST サーバーを立ち上げる
1．CA\app_ca_pem.py  これは必須
2．login\app_login.py  これも必須 
3．app_flask.py  これがテストサーバー
※　これ以外は立ち上げなくてもテストはできる。

(.venv312) D:\city_chain_project\login\client_code\android>python app_flask.py
 * Serving Flask app 'app_flask'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.3.8:5000
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 114-323-945

という具合に、app_flask.pyから5000に入る。

✅ 最後に確認：Android 側の BASE_URL 設定
private const val BASE_URL = "http://192.168.3.8:5000/"

//  app/src/main/java/com/example/test100mb/network/ApiClient.kt　に記載がある。

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    private const val BASE_URL = "http://192.168.3.8:5000/"

    private val retrofit: Retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val authService: AuthApiService = retrofit.create(AuthApiService::class.java)
    val storageService: StorageApiService = retrofit.create(StorageApiService::class.java)
}

# 接続エラーの対処方法
この java.net.SocketException: socket failed: EPERM (Operation not permitted) エラーは、Android 実機から PC の Flask サーバーにソケット接続できないことが原因です。

これは、Android 13以降のセキュリティ強化・ネットワーク制限や、Flaskの起動方法・ネットワーク構成・パーミッションの不備が絡んでいます。ひとつずつ潰しましょう。

✅ すぐ確認するべき 7 項目
① Flask サーバーは 0.0.0.0 かつ port=8888 で起動しているか？
あなたのコードでは port=8888 にしていても、ログ上で http://127.0.0.1:5000 が表示されていたらダメです。

正しい起動ログ：
 * Running on http://192.168.3.8:8888
それが出ていなければ：
app.run(host="0.0.0.0", port=8888, debug=True, use_reloader=False)
で 確実に再起動抑制つきで起動してください。

② Android 側の BASE_URL は正しいか？
const val BASE_URL = "http://192.168.3.8:8888/"
と必ず / を含めて明示しましょう。

③ AndroidManifest.xml に INTERNET 権限はあるか？
<uses-permission android:name="android.permission.INTERNET" />
これがなければ外部通信は絶対にできません。

④ androidTest 実行中の対象クラスは @RunWith(AndroidJUnit4::class) をつけているか？
@RunWith(AndroidJUnit4::class)
class StorageApiServiceIntegrationTest { ... }

⑤ Android 13 (API 33+) の場合、ネットワークセキュリティ設定を追加しているか？
res/xml/network_security_config.xml を作成：
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">192.168.3.8</domain>
    </domain-config>
</network-security-config>

AndroidManifest.xml に反映：
<application
    android:networkSecurityConfig="@xml/network_security_config"
    android:usesCleartextTraffic="true"
    ... >

⑥ Android と PC は同じ Wi-Fi セグメントか？
IP がそれぞれ：
PC → 192.168.3.8
Android → 192.168.3.7
なら 同じネットワーク内 なので OK。

⑦ Flask が Windows Defender や VPN にブロックされていないか？
確認方法：
一時的に Windows Defender ファイアウォール無効化
curl http://192.168.3.8:8888/ を スマホの Chrome で叩いてみる → Flask is running... が出れば OK


6️⃣ ファイル保存を目視確認
Android Studio ▸ View ▸ Tool Windows ▸ Device File Explorer
/data/data/com.example.test100mb/files/

以下ファイルが存在するか確認（rsa/ はサブフォルダ）
client_certificate.pem
ntru_private_key.pem
dilithium_private_key.pem
dilithium_secret_key.pem
rsa/rsa_private_key.pem
rsa/rsa_public_key.pem
reserve.bin
端末が root 化されていない場合、実機では表示されません。その場合は adb shell run-as com.example.test100mb ls -R files で確認できます。

7️⃣ もしファイルが無い／ログイン失敗するとき
チェック項目	対処法
HTTP 401 / 404	ユーザー名・パスワード・BASE_URL を再確認
KeyFileManager.storeAll が try-catch で握り潰し	
"Logcat(View→　window Tools→　Logcat)" の KeyFileManager / DilithiumSecretKeyStore タグを検索
dilithium_secret_key.pem が無い	/user/keys/update のレスポンスや RSA 復号で例外が無いか Logcat を確認
reserve.bin が無い	ストレージフルで作成失敗 → FileManager.reserveSpace の例外を Logcat でチェック

✅ 完了チェック
 /user/login が 200 OK で証明書＋鍵が返る
 files/ に 6 つのファイルが確認できる
 アプリが MainActivity へ遷移




# 「Androidアプリの無料作成と本番リリース（Playストア配信）」について、以下の 5ステップの流れ でご案内します。

✅ ステップ1：Androidアプリの本番用UIを作成する
目標：テストコード（InstrumentationTest）で行った
/register/、/user/login、/user/storage_check のフローを
GUIで操作できるアプリにします。

Python側に既に .html（ログイン画面など）がある場合、Androidアプリに移行する際の画面（UI）との関係は以下のようになります：
✅ 結論：Androidアプリでは .html は使いません
Androidアプリは、HTMLベースの画面ではなく、
XML + Kotlin（または Java）でネイティブ画面を作成します。

🔄 WebとAndroidの画面の違い・役割対応表
機能/画面	Python側（Flask + HTML）	Android側（ネイティブアプリ）
ログイン画面	login.html など	LoginActivity.kt + activity_login.xml
登録画面	register.html	RegisterActivity.kt + activity_register.xml
鍵管理画面	user_keys.html など	KeyUpdateActivity.kt（API 呼び出し）
ストレージ通知	storage_check.html 等	StorageCheckActivity.kt（予約ボタン）

🧠 理解のポイント：AndroidはAPIと通信するだけ
Flaskサーバーにある .html ファイルは、Webブラウザ用のUI
Androidは .html を直接使わず、Retrofit + OkHttp で Flask の API を直接呼び出す
Android側は UIだけ別に再構築する必要がある

✅ 対応方法（画面をAndroidで作る）
例：Flaskの /user/login を使ってログインする場合
画面要素	Flask（Web）	Android（ネイティブ）
ユーザー入力欄	<input type="text">	<EditText android:id="@+id/username">
パスワード入力欄	<input type="password">	<EditText android:id="@+id/password">
送信ボタン	<form action="/user/login">	<Button android:onClick="login()">
ロジック	Flask側のPOST	RetrofitでPOSTリクエスト送信

🔧 どうするか？
Android Studioで以下のActivityを追加していきます：
LoginActivity.kt
RegisterActivity.kt
KeyUpdateActivity.kt
StorageCheckActivity.kt
Flaskサーバー側のAPI (/register, /user/login, /user/keys/update, /user/storage_check) は そのまま利用できます
.html はAndroidアプリにおいては参照しないので、あくまでWebUIが必要なとき用に残しておけばOKです。


▼ 構成案（シンプルなUI構成）
画面名	機能内容
起動画面	初期設定、内部鍵ファイル確認など
ユーザー登録画面	ユーザー名、メール、パスワード入力 → register
ログイン画面	ユーザー名、パスワード入力 → JWT取得、鍵保存
ストレージチェック画面	予約サイズを送信（ボタン1つ）

▼ 実装のポイント
Activity や ViewModel を使い、Retrofit+OkHttp で API 呼び出し
テストコードの ApiClient を共通化して再利用可能（UIから叩く）

✅ ステップ2：Google Play Console に登録する（無料）
内容	詳細
URL	https://play.google.com/console
必要	Google アカウント + 開発者登録（初回のみ25 USD、永年）
ポイント	アプリを公開・管理するために必須のポータルです
※ 無料でダウンロード可能なアプリを配信できます（課金しなければ費用ゼロ）

✅ ステップ3：アプリに署名してリリースビルドを作成する
Androidアプリは公開用に署名付きリリースAPKまたはAABファイルが必要です。
▼ 手順概要（Android Studio）
メニュー → Build → Generate Signed Bundle / APK
.jks キーストアファイルを作成（初回）
リリースビルド（AAB推奨）を生成
Google Play Console にアップロード

✅ ステップ4：Google Play にアップロードして審査を受ける
▼ 必要なもの
アプリ名、説明、スクリーンショット
APK/AABファイル（署名済み）
プライバシーポリシー（例：GitHub Pages などに用意）
テスト端末がある場合、内部テスト or クローズドテストから配信可能

✅ ステップ5：ユーザーがインストールできるようになる
審査完了後、Google Play上に公開され、誰でもインストール可能になります。
ダウンロード数に応じてサーバー負荷テストが可能
Firebase Crashlytics などでクラッシュ状況も追跡可能
アップデートも簡単に差し替えできます

🚀 最初に取り掛かること（次のアクション）
MainActivity.kt に UI画面を追加
既存の ApiClient.kt を UI用に移植
ユーザー入力（EditText）から登録・ログインを行えるようにする
レイアウト（activity_main.xml）を用意してボタン配置

ご希望があれば、
📱**「本番用アプリのソースコード雛形」**
をすぐに作成して差し上げます。ご要望があればお知らせください！
