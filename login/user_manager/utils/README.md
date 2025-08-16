# 2. login_app/app_login.py 側の login_bp と何が違うのか？
app_login.py の login_bp
フロントエンド画面 (HTML テンプレート) と連動して

/login/ の GET でログインフォームを返し

/login/ の POST でワンタイム認証や２段階認証を含むフローを制御
といった、ユーザー向け Web アプリケーション本体の「ログイン画面」「ログイン API」を担います。

utils/login_handler.py (device_auth_bp)
IoT やゲーム機、TV などの**外部端末（ウェブ画面を持たないクライアント）**が

端末の空きストレージを報告し

ユーザー名／パスワード／証明書指紋を POST する
…といった、組み込みデバイス向けの軽量認証＋ストレージチェックに特化したマイクロサービス的エンドポイントです。

つまり、

名前は似ていますが用途が異なる（一方はブラウザ画面+フォーム用、もう一方は外部端末用 API）。

Blueprint 名や URL プレフィックスを分けておけば、同じ「login_bp」という名称衝突も起きませんし、動かすサーバーを分けても構いません。

✅ カーナビやゲーム機・IoTデバイスで使える「メモリ的」な保存方法
手段	実現方法例	安全性	コメント
内蔵 Flash/eMMC に保存	アプリの内部ストレージ領域にファイルとして保存	○	最も現実的な方式。盗難時注意
環境変数に保存	OSのブート時に環境変数として読み込む	△	一時的で再起動で消える
EEPROMに保存	少量の鍵をバイナリで保存可能	○〜◎	家電やセンサーで利用可
Web Storage系（PWA）	WebViewアプリなら IndexedDB や Cache API	○	スマートTVやスマート家電

✅ 選択肢：ディスク以外に保存できる場所（端末別）
保存先	層	特徴	対象端末の例
RAM	揮発性	一時的な記憶、電源OFFで消える	一時署名処理で有効
Flash (eMMC/NAND)	永続的	内蔵ストレージ、HDD/SSDの代替	IoT・スマートスピーカー等
Secure Element (SE)	ハード	暗号鍵用専用チップ（鍵焼き込み可）	カーナビ・ゲーム機・車載端末
TPM / HSM	ハード	暗号計算専用、安全な鍵格納	一部の高級PC・法人IoT
EEPROM	ハード	少量のデータを永続保存（数KB程度）	家電・センサー
Firmware領域	ソフト/ROM	ソフト的に鍵を埋め込み（アップデート難）	工場出荷時固定キー等

login/
 └─ user_manager/
     └─ utils/
         ├─ platform_utils.py
         ├─ storage_checker.py
         ├─ login_handler.py
         └─ test_utils.py
 └─ client_code/
     ├─ pc_check.py
     ├─ android_check.kt
     ├─ ios_check.swift
     ├─ game_check.c
     └─ README.md (任意で追加の説明を入れても良い)

# Client Code for Storage Checking

各端末ごとに実装例をまとめたディレクトリです。

- **pc_check.py**:  
  Windows/Mac/Linux PC で Python を使い、`shutil.disk_usage` により空き容量を計算 → サーバーへPOST。

- **android_check.kt**:  
  Kotlin で `StatFs` を使い、アプリ内部領域の空き容量 (bytes) を取得 → OkHttp でサーバーへPOST。

- **ios_check.swift**:  
  Swift で `FileManager` や `resourceValues(volumeAvailableCapacityForImportantUsageKey)` を使い空き容量を取得 → `URLSession` でサーバーへPOST。

- **game_check.c**:  
  Linux系の statvfs により空き容量を取得 → libcurl で JSON POST。
  （PlayStation, Xbox, Switch 等 公式SDK では手法が異なる場合が多いのでカスタマイズが必要）

## How to Use

1. それぞれの端末上で、対応するコードをビルド / 実行。  
2. サーバー (Flask) 側は `login_handler.py` を起動しておく。  
3. クライアントが送る `client_free_space` (バイト数) をもとに、サーバーが 100MB 以上か判定。  
4. OK なら 200、足りなければ 403 を返す。  

## Note

- 本例ではデモ用に認証をダミー実装 (admin/password) としているが、本番ではセキュアな認証手法を適用してください。  
- 実際のゲーム機やスマホではサーバーと同居しないことが多いため、ローカルでの ctypes 呼び出しは行わず、クライアント側のネイティブ API で空き容量を取得するのが通例です。

# test
test_utils.py は、あくまで login_handler.py を起動してそこに対してリクエストを投げるだけのテストです。ですので、事前に立ち上げておくべき「サーバー」は login_handler.py だけです。以下の要点を押さえてください。
(.venv312) D:\city_chain_project\login\user_manager\utils>python login_handler.py
[INFO] ca_issue_client_cert_asn1.py loaded
 * Serving Flask app 'login_handler'
 * Debug mode: on
[INFO] 2025-05-07 06:46:16,033 - [31m[1mWARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.[0m
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5050
 * Running on http://172.21.2.182:5050
[INFO] 2025-05-07 06:46:16,033 - [33mPress CTRL+C to quit[0m
[INFO] 2025-05-07 06:46:16,048 -  * Restarting with stat
[INFO] ca_issue_client_cert_asn1.py loaded
[WARNING] 2025-05-07 06:46:18,423 -  * Debugger is active!
[INFO] 2025-05-07 06:46:18,611 -  * Debugger PIN: 114-323-945


(.venv312) D:\city_chain_project\login\user_manager\utils>pytest -v test_utils.py
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.3.5, pluggy-1.5.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project\login\user_manager\utils
collected 2 items

test_utils.py::TestLoginHandler::test_login_pc_storage_and_auth PASSED                                           [ 50%]
test_utils.py::TestLoginHandler::test_login_android_storage_and_auth PASSED                                      [100%]

================================================== 2 passed in 2.61s ==================================================
