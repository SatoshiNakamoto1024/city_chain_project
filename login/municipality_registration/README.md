位置情報を扱う方法は大きく分けて２通りあります。以下、それぞれのメリット／デメリットと、どちらが現実的かをまとめてみました。

1. コード＋プルダウン方式（いままでの JIS コード／階層選択）
メリット
実装がシンプル
JSON や DynamoDB にあらかじめリストを置いておいて、フロント→バックエンド間でコードを渡すだけ。外部 API は不要です。

入力品質が高い
ユーザーが入力ミスしにくく、正規化されたコードデータ（JIS や ISO）なのでバリデーションも楽。

オフライン対応しやすい
地図やジオコーディングサーバーにアクセスしなくても動きます。

運用コストが低い
ジオポリゴンやタイルサーバーを立てる必要が無く、データも JSON ファイル数 MB 程度。

デメリット
一覧メンテナンスが必要
新しい市町村や国・都道府県コードの更新を定期的に取り込む必要があります。

自由度が低い
緯度経度など座標情報は持たないので、地図上ピンを打つ／近隣検索といった機能は別実装が必要。

2. ポリゴン／GPS 逆ジオコーディング方式
メリット
地理的に柔軟
GPS で拾った緯度経度をベースに、その座標がどの「市町村ポリゴン」に入っているかを判定できる。

地図連携が容易
Leaflet や Mapbox GL などで地図を表示し、ユーザーの現在地をそのまま絞り込みに使える。

メンテ不要
一度ポリゴンデータ（GeoJSON）を揃えれば、あとはコード・名称の更新コストはほぼゼロ。

デメリット
初期構築コストが高い
・全世界／国内の行政区分ポリゴンデータ（GeoJSON/Shapefile）を集める
・ジオスペーシャル DB（PostGIS, MongoDB の GeoJSON）や演算ライブラリが必要

運用負荷が増大
座標判定クエリ（ポイントインポリゴン）には CPU 負荷がかかる。
タイルサーバーを自前で運用するならインフラコストも必要。

外部サービス依存
Google Maps や AWS Location Service 等の逆ジオコーディング API を使う場合、呼び出し料が発生。

どちらが現実的か？
大半の業務系アプリ では、コード＋プルダウン方式で十分に要件を満たせます。
└→ 入力強制・バリデーションのしやすさ、メンテコストの低さから、特に行政区分が明確な日本国内向けサービスではこちらがオススメ。

位置情報をメインに扱う（地図表示／近隣検索／モバイルアプリ） 場合や、
ユーザーの現在地から自動判定 したいなら、ポリゴン／GPS 方式が向きます。
ただしベース構築と運用が大きく増えるため、まずはコード選択方式で MVP を作り、後から必要に応じて GPS 連携を検討すると良いでしょう。

私のおすすめ
最初は「JIS コード＋プルダウン」で実装して、入力フローを固める。
そのうえで「地図／GPS」を追加する段階を別フェーズとして切り分ける。

この順序であれば、いきなり地理ポリゴンの山を越える必要がなく、かつ将来的に GPS ベースもスムーズに導入できます。


#　あなたが構築しているのは、市町村単位で分散参加可能な地球規模の分散型自治ネットワークです。
そのために必要なのは：

✅ 目的（整理）
1. 市町村の登録（municipality_registration/）
→ 登録されると、大陸/国/都道府県/市町村の情報が DynamoDB (Municipalities) に保存される。

2. 市町村職員の登録（municipality_verification/）
→ 対応する市町村に紐づく形で職員が登録される。MunicipalStaffs に保存される。

3. ユーザー登録（registration/）
→ ユーザーは、登録時に「大陸 > 国 > 都道府県 > 市町村」を絞り込み選択する UI（セレクトボックス）が必要。

4. DApps（送信フォームなど）でも同じ流れで絞り込み検索
→ ユーザー選択画面では1億人中の1人を効率的に探すためにこの多段階絞り込みが必須。

✅ 登録の流れ（整理）
1. /municipality_registration → 市町村が参加を宣言（大陸、国、都道府県、市町村）
    → DynamoDB(Municipalities) に保存
    → region_tree.json のようなファイルを自動更新

2. /municipality_verification → 市町村職員がログイン・ユーザーを承認

3. /registration → 市民ユーザーが「大陸 > 国 > 都道府県 > 市町村」をプルダウンで選び、登録

4. /sending_dapps → 送信時にも「大陸 > 国 > 都道府県 > 市町村 > ユーザー名」の順に絞って選択

✅ 次のステップ
今あなたが必要としているのは、ステップ1：municipality_registration モジュールの本番実装です。
📁 municipality_registration/ フォルダ構成とコード一式（修正済・本番対応）
app_municipality_registration.py （Flaskアプリ）
routes.py（HTMLテンプレート連携）
models.py（DynamoDB登録処理）
config.py
templates/municipality_register.html（本番UIでの登録画面）
region_tree_updater.py（登録された市町村を JSON に反映）

その後、registration/ や dapps/ での絞り込みプルダウン UIとの接続も進めます。
必要であれば、S3やAPI Gatewayからフロントにregion_tree.jsonを提供する構成も提案できます。


# 修正後は、
フロント側は JIS JSON (continents.json, countries.json…etc.) だけを参照し、
登録API は必須項目を受け取って DynamoDB に書き込み → region_tree.json は 登録後 にのみ update_region_tree で追記
という動きになります。


municipality_registration/service.py の register_municipality を呼び出し
テストではこちらを呼び、同時に
Municipalities テーブルに市町村レコードを追加
MunicipalStaffs テーブルに職員レコード（staff_id + staff_password）を追加
してくれるため、独自に職員登録ロジックを書く必要がなくなりました。

# ログイン処理 (municipality_login.py)
/staff/login の GET: staff_login.html を返す
/staff/login の POST: JSON で {staff_id, password, municipality} を受け取り、
DynamoDB (MunicipalStaffs テーブル) から該当する行を取得
パスワードをハッシュ比較し、一致すれば JWT (ペイロードに staff_id) を返す

# 承認処理 (views.py + approval_api.py + verification.py + municipality_tools/municipality_approval_logger.py)
/staff/verify の GET: staff_verify.html を返す
/staff/verify の POST: Authorization ヘッダーから Bearer <JWT> を取り、staff_id を取得
JSON で {uuid, action} を受け取り (action は "approve" または "reject")
DynamoDB (UsersTable) の approval_status を "approved" / "rejected" に更新
承認ログ (MunicipalApprovalLogTable) に記録

# テスト (test_municipality_verification.py)
事前に register_municipality を呼んで市町村と職員を一気に登録
/staff/login で JWT を取得
UsersTable に直接 pending ステータスのユーザーを作成
/staff/verify で承認操作 → DynamoDB に反映されているか・ログが残っているかをチェック

# 環境変数の読み込み
config.py や municipality_tools/* ではすべて os.getenv(...) を使っているので、
テスト実行前に環境変数（AWS_REGION, USERS_TABLE, STAFF_TABLE, APPROVAL_LOG_TABLE, JWT_SECRET, JWT_ALGORITHM など）をセットすれば問題なく動作します。

# ファイル配置
templates/ ディレクトリには staff_login.html と staff_verify.html を置き、
Flask アプリ起動時には template_folder="templates" を正しく指定してください。テストでも template_folder を絶対パスで渡しているのでテンプレートが見つかります。

以上で、municipality_verification/ 以下の修正後ファイルをすべて掲載しました。
これを配置して、あらためて以下を実行すればテストがパスするはずです。

bash
Copy
Edit
(.venv312) $ cd municipality_verification
(.venv312) $ pytest -v test_municipality_verification.py
もし追加の環境変数設定が必要な場合は、テスト実行前にシェルなどで export（Windows なら set）してください。

参考：テスト実行に必要な DynamoDB テーブル構造
UsersTable

PK: uuid (S)

RangeKey: session_id (S)

属性: approval_status (S), tenant_id (S), certificate (Map), など

MunicipalStaffs

PK: staff_id (S)

RangeKey: municipality (S)

属性: password_hash (S), salt (S), name (S), email (S), created_at (S)

MunicipalApprovalLogTable

PK: log_id (S)

その他: uuid, action, approver_id, reason, client_ip, timestamp

Municipalities（register_municipality が書き込む）

PK: municipality_id (S)

RangeKey / その他: municipality_name (S), continent (S), country_code (S), …, created_at (S)

テスト環境で上記テーブルを先に作成し、README やテストセットアップスクリプトなどで準備しておくとスムーズです。これで全ファイルの修正版を入れ終わりました。