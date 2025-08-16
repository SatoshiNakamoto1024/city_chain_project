poh_metrics/                                 ← リポジトリ・ルート
├── LICENSE                                 ← ライセンス (Apache-2.0 など)
├── README.md                               ← パッケージ概要・インストール手順・使い方
├── .gitignore                              ← __pycache__/、*.py[cod]、dist/ など
├── pyproject.toml                          ← PEP 517/518 ビルド設定／依存関係／プロジェクトメタデータ
└── poh_metrics/                            ← 実際の Python モジュール
    ├── __init__.py                         ← バージョン定義など
    ├── types.py                            ← 各メトリクスのラベル型定義 (PoHResult, GcEvent など)
    ├── registry.py                         ← Prometheus CollectorRegistry のラッパー
    ├── metrics.py                          ← カウンタ／ゲージ／ヒストグラム定義と登録関数
    ├── collector.py                        ← アプリコードから呼び出す API (`increment_poh()`, `observe_latency()` など)
    ├── exporter.py                         ← `aiohttp` ベースの `/metrics` HTTP サーバーエンドポイント
    ├── middleware.py                       ← (オプション) Web サーバー用ミドルウェアでリクエスト計測
    └── tests/                              ← 単体テスト
        ├── __init__.py
        ├── test_types.py                   ← `types.py` のバリデーション／変換テスト
        ├── test_registry.py                ← `registry.py` のシングルトン性、手動プッシュ機能テスト
        ├── test_metrics.py                 ← メトリクス定義・ラベル付与テスト
        ├── test_collector.py               ← `collector.py` API 呼び出しが正しくメトリクスを増減するか
        ├── test_exporter.py                ← `/metrics` エンドポイントの非同期取得テスト
        └── test_middleware.py              ← ミドルウェア計測が呼び出されるかのテスト

フェデレーションモデル + DAG（Directed Acyclic Graph）における Proof of History (PoH) の使い道、しっかり整理して答えます。

✅ 1️⃣ フェデレーションモデル + DAG とは
まず整理：
フェデレーションモデル
→ 市町村・州・国など、複数の独立ネットワークが連携する階層構造
→ 例：Municipality Chain → Continental Chain → Global Chain

DAG
→ ブロックチェーンよりも柔軟・並列化されたデータ構造
→ 各トランザクションは他の1つまたは複数のトランザクションを参照（親にする）
これにあなたの持つ Proof of Hold (PoHold) などの「保有証明」系アルゴリズムを載せるのが基本の流れですよね。

✅ 2️⃣ DAG内で Proof of History (PoH) を使う意義
DAGの課題は以下です：
並列化が進むほど「どの順で何が起きたのか」の全体履歴が見えにくくなる
特にフェデレーション間（例：市町村チェーン間）の統合時に「順序の確定」が必要
ここで PoH が役立つのは：
✨ フェデレーション統合の順序保証レイヤー ✨

具体的には：
✅ 各Municipality Chain内はDAGで並列処理
✅ Continental Chainに統合する際、Municipality ChainのDAGヘッダーをPoHで時系列化
✅ Global ChainではPoHでContinental Chainヘッダーを連結

つまり PoH を「DAG間を繋ぐ順序保証のためのタイムスタンプチェーン」として使う、という役割です。

✅ 3️⃣ 具体例：どこでどう使えるか
レイヤー	DAG構造	PoHの役割
Municipality Chain	個人/団体間のトランザクション（並列）	内部では不要（PoHoldやPoPlaceが主役）
Continental Chain (統合層)	各市町村DAGから集約されたヘッダーを並列保持	集約ヘッダーの順序をPoHで証明する
Global Chain (最上位)	各大陸DAGのヘッダーを並列保持	大陸間統合の順序をPoHで証明する

例えば：
市町村A → 市町村B → 大陸X → Global
このとき、市町村内の詳細トランザクションはDAG、
市町村の「まとめブロック」の順序付けにPoH、
大陸の「まとめブロック」の順序付けにもPoHを適用。

✅ 4️⃣ なぜPoHoldだけでは不十分？
PoHoldは「ノードがちゃんと保持しているか（信頼性・貢献度）」の証明です。
一方でPoHは「ネットワーク全体の順序を最小コストで保証する」仕組みであり、
特に並列化が強いDAGの上層で：
最終決済順序の確定
不正ノードが横から無関係なデータを突っ込む防止
クロスフェデレーション同期の効率化
に役立ちます。

✅ 5️⃣ 導入案
もし興味があれば、設計例を作ります。
例：
poh_header_service.py → 各Municipality DAGのヘッダーを集めてPoHを作成するモジュール
global_chain_poh_verifier.py → Global層で各大陸ヘッダーのPoHを確認するモジュール
Prometheus連携で poh_block_count や poh_verification_latency をメトリクス化

💡 結論
✅ あなたのDAGフェデレーションモデルには PoHの使い道がある
✅ 特に Municipality-DAG → Continental-DAG → Global-DAG の統合部分の順序保証に使える
✅ PoHoldはノード単位の貢献証明、PoHはネットワーク間の履歴証明という「別方向の補完関係」

| 項目        | Proof of History (PoH) | Proof of Hold (PoHold)  |
| --------- | ---------------------- | ----------------------- |
| 目的        | 時系列の順序証明（例：Solana）     | 保有・保持の証明（例：一定時間トークン保持）  |
| 典型用途      | 高速チェーンのトランザクション順序付け    | DAGやネットワークでの信頼性・貢献度証明   |
| 必要なメトリクス例 | 発行数、検証レイテンシ、リクエスト数など   | 保有時間、ホールド開始/終了、貢献ポイントなど |


#　poh_metrics (proof of History 版)　概要
ではここで、poh_metrics クレート（Python パッケージ）の機能を詳しく分かりやすく解説します。
🏗️ 全体像 (注意！proof of hold ではなく、historyの方です！)
poh_metrics は
Proof of History (PoH) サービス用の Prometheus メトリクス収集と HTTP/gRPC 統計の提供モジュール
です。

役割は大きく分けて4つ：
レイヤー	内容
metrics.py	メトリクス定義と登録、安全な取得ヘルパ
collector.py	アプリ側から呼ぶ非同期 API（例：カウンタ増加、遅延観測）
middleware.py	aiohttp middleware / gRPC interceptor（HTTP/gRPC リクエスト数・遅延記録）
tests/	各モジュールの pytest テストスイート

🔧 metrics.py（メトリクス定義・登録）
このファイルは Prometheus 用のカウンタ・ヒストグラム・サマリ・ゲージを定義 します。
登録するメトリクス例：
poh_issued_total — 発行 PoH 数（Counter）
poh_issue_latency_seconds — PoH 発行レイテンシ（Histogram）
poh_issue_latency_summary_seconds — PoH 発行レイテンシ（Summary）
poh_verify_latency_seconds — PoH 検証レイテンシ（Histogram）
gc_events_total — ガーベジコレクションイベント数（Counter）
active_peers — 接続中のピア数（Gauge）
http_requests_total — HTTP リクエスト数（Counter）
grpc_requests_total — gRPC リクエスト数（Counter）

特徴：
✅ 二重登録を防ぐ
✅ 必要時に自動登録・取得する (get_metric)

🚀 collector.py（非同期ヘルパ）
アプリのサービス層や API 実装から呼び出すための async ヘルパ関数群 です。
主な関数：
関数	内容
increment_poh	PoH 発行件数を +1 する
observe_issue	PoH 発行レイテンシ（秒）を記録
observe_verify	PoH 検証レイテンシ（秒）を記録
record_gc	GC イベントを +1（type: minor/major などラベル付け）
set_active_peers	ピア数をセット（Gauge なので動的変更OK）
アプリ側では直接メトリクスを触らず、これを介すことで安全に記録できます。

🌐 middleware.py（HTTP/gRPC 用ミドルウェア）
aiohttp middleware
各 HTTP リクエストの:
件数（成功・失敗）を http_requests_total に記録
レイテンシを observe_verify に流用（成功/失敗判定付き）
grpc.aio.ServerInterceptor
各 gRPC メソッドの:
件数（メソッド名・ステータスコード付き）を grpc_requests_total に記録
レイテンシを observe_verify に流用
これにより、アプリ全体の統計情報が自動的に取れる 仕組みになります。

🧪 tests/（テスト群）
pytest + pytest-asyncio を使い、各モジュールの単体テストを完備。
例：
collector の各関数が正しくメトリクスを書き込むか？
middleware 経由で HTTP 500 や 200 で記録が分かれるか？
registry に期待通りのメトリクスが登録されるか？
CI（GitHub Actions）と合わせて、本番品質の保守 に役立ちます。

💡 利用イメージ
from poh_metrics.collector import increment_poh

await increment_poh("success")  # 発行成功を記録

または
from aiohttp import web
from poh_metrics.middleware import metrics_middleware

app = web.Application(middlewares=[metrics_middleware])

⚡ 強みまとめ
✅ Prometheus 対応の標準設計
✅ HTTP・gRPC を横断した統計記録
✅ 非同期対応（FastAPI, aiohttp, gRPC aio サーバーなどと相性抜群）
✅ CI 付きで安全性・品質担保


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

#　wheel を dist\ に置きたいなら
pip install -e .
python -m build --wheel --outdir dist（Python ラッパも含め全部）

pytest 用単体テスト。
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\pytest poh_metrics/tests

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_metrics>pytest poh_metrics/tests -v
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project\DAGs\libs\algorithm\poh_metrics
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 8 items

poh_metrics/tests/test_collector.py::test_collector_functions PASSED                                             [ 12%]
poh_metrics/tests/test_exporter.py::test_exporter_endpoint PASSED                                                [ 25%]
poh_metrics/tests/test_metrics.py::test_metrics_registered PASSED                                                [ 37%]
poh_metrics/tests/test_middleware.py::test_http_middleware PASSED                                                [ 50%]
poh_metrics/tests/test_registry.py::test_singleton_registry PASSED                                               [ 62%]
poh_metrics/tests/test_registry.py::test_set_and_push_metrics PASSED                                             [ 75%]
poh_metrics/tests/test_types.py::test_pohresult_literals PASSED                                                  [ 87%]
poh_metrics/tests/test_types.py::test_gctype_literals PASSED                                                     [100%]

================================================== 8 passed in 0.69

#　1. WSL のセットアップ
/ 4.24.4 ソースを C 拡張スキップ でビルド
pip uninstall -y protobuf
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
pip install protobuf==5.27.0
REM ↑ 変数のおかげでランタイムでは純 Python 実装のみロードされる
手元で wheel をビルドしないので Visual C++ エラーは出ない

WSL の有効化
管理者 PowerShell を開き、以下を実行：
PS C:\WINDOWS\system32> wsl --install

これで既定のディストリビューション（Ubuntu）がインストールされ、再起動後にユーザー設定（UNIX ユーザー名／パスワード）を求められます。

Ubuntu の起動
スタートメニューから「Ubuntu」を起動。
sudo apt update && sudo apt upgrade -y
PW: greg1024

(よく切れるので、切れたらこれをやる)
# 1) ビジーでも強制的にアンマウント
deactivate          # venv を抜ける
sudo umount -l /mnt/d      # ← l (エル) オプション
# 2) 改めて Windows の D: をマウント
sudo mount -t drvfs D: /mnt/d -o metadata,uid=$(id -u),gid=$(id -g)

Python3.12 のインストール
Ubuntu のリポジトリによっては最新が入っていないので、deadsnakes PPA を追加しておくと便利です：
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv
sudo apt install python3-distutils

python3.12 コマンドで起動できるようになります。

pip と仮想環境の準備
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.12
python3.12 -m venv ~/envs/linux-dev
source ~/envs/linux-dev/bin/activate

2. プロジェクトをクローン／マウント
Windows 上のソースコードディレクトリ
たとえば D:\city_chain_project\DAGs\libs\algorithm\ 配下にあるなら、WSL 側からは
/mnt/d/city_chain_project/DAGs/libs/algorithm/ でアクセスできます。
下記のようになればOK
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_metrics$

各クレート（poh_storage/、poh_ttl/、poh_network/）それぞれで editable インストール：
# 例: poh_storage
cd poh_storage
　※プロジェクトの test extras をまとめて拾ってくる
pip install -e '.[test]'
python -m pytest poh_storage/tests

# 同様に poh_ttl
cd ../poh_ttl
pip install -e '.[test]'
python -m pytest poh_ttl/tests

# 同様に poh_types
cd ../poh_types
pip install -e '.[test]'
python -m pytest poh_types/tests

# そして poh_metrics
cd ../poh_metrics
pip install -e '.[test]'
#　wheel を dist\ に置きたいなら comandプロンプトから（ややこしいね。。）
pip install -e .
python -m build --wheel --outdir dist（Python ラッパも含め全部）

#　テストはWSL から
python -m pytest poh_metrics/tests
