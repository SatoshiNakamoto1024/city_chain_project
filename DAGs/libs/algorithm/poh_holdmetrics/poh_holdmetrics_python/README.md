※　Windows側がC拡張処理できず未build

poh_holdmetrics/                                 ← リポジトリルート
├── README.md                                    ← プロジェクト概要・使い方
├── LICENSE                                      ← Apache-2.0 など
├── poh_holdmetrics_integration.py               ← Rust↔Python 結合シナリオ（pytest で実行）
├── .gitignore                                   ← /target, __pycache__, *.so, dist/
├── .github/
│   └── workflows/
│       └── ci.yml                               ← cargo test → maturin build → pytest → cargo bench
│
├── poh_holdmetrics_rust/                        ← Rust コア & PyO3 バインディング
│   ├── Cargo.toml                               ← crate 名: poh_holdmetrics_rust
│   ├── pyproject.toml                           ← maturin-build設定（abi3-py312）
│   ├── build.rs 
│   ├── benches/
│   │   ├── bench_holdmetrics_calc.rs            ← スコア計算性能測定
│   │   └── bench_holdmetrics_parallel.rs        ← 並列集計ベンチ
│   ├── src/
│   │   ├── lib.rs                               ← `pub mod holdset; pub mod error; pub use holdset::*;`
│   │   ├── holdset.rs                           ← 保有時間→ポイント算出アルゴリズム（高速化部分）
│   │   ├── grpc.rs                              ← grpc exporting
│   │   ├── model.rs                            ← Shared data structures
│   │   ├── metrics.rs                           ← Prometheus gauge ・ counter initialisation
│   │   ├── error.rs                             ← `thiserror::Error` 共通エラー
│   │   ├── bindings.rs                          ← `#[pymodule]`・`#[pyfunction]` PyO3 ラッパ
│   │   └── main_holdmetrics.rs                  ← `--bin main_holdmetrics` CLI デモ
│   └── tests/
│       ├── test_cli.rs
│       ├── test_import.rs
│       ├── test_metrics.rs                      ← Prometheus メトリクス テスト
│       ├── test_grpc.rs                         ← gRPC I/O テスト
│       ├── test_py_bindings.rs
│       └── test_holdmetrics.rs                  ← Rust 単体テスト
│
└── poh_holdmetrics_python/
    ├── pyproject.toml                           ← Poetry/ Hatch 等 (poh-holdmetrics 名)
    ├── README.md                                ← pip インストール例・API 使用例
    └── poh_holdmetrics/                         ← Python パッケージ & 周辺ユーティリティ
        ├── __init__.py                              ← Rust 拡張のリロード & 公開 API
        ├── _version.py                              ← 自動生成版 + `importlib.metadata`
        ├── config.py                                ← TOML/YAML + env 取り込み
        ├── data_models.py                           ← Pydantic: HoldEvent / HoldStat …
        ├── tracker.py                               ← 非同期保持トラッカー (`record_start/stop`)
        ├── calculator.py                            ← Rust FFI 経由スコア計算 + fallback Pure-Py
        ├── scheduler.py                             ← `asyncio.TaskGroup` 周期集計・GC
        ├── app_holdmetrics.py                       ← `python -m poh_holdmetrics.app_holdmetrics` CLI
        │
        ├── exporter/                                ← 可観測性レイヤ
        │   ├── __init__.py
        │   ├── prometheus.py                        ← /metrics エンドポイント
        │   └── otlp.py                              ← OTEL Push / Pull
        │
        ├── storage/                                 ← プラガブル永続化
        │   ├── __init__.py
        │   ├── mongo.py                             ← motor 非同期ドライバ
        │   └── immudb.py                            ← aiogrpc → immuDB
        │
        ├── api/                                     ← ネットワーク I/F
        │   ├── __init__.py
        │   ├── grpc_server.py                       ← AIO gRPC: HoldEvent ストリーム
        │   └── http_server.py                       ← FastAPI: /hold, /stats, /healthz
        │
        ├── protocols/                               ← Protobuf 生成物（自動生成ディレクトリごと commit）
        │   ├── hold.proto
        │   └── hold_pb2_grpc.py
        │
        ├── storage/                               
        │   ├── immudb.py
        │   └── mongodb.py
        │
        └── tests/                                   ← pytest & pytest-asyncio
            ├── __init__.py
            ├── test_tracker.py
            ├── test_calculator.py
            ├── test_scheduler.py
            ├── test_storage.py
            └── test_api.py

1. ドメインモデル — data_models.py
クラス	フィールド	目的
HoldEvent	token_id, holder_id, start, end, weight	「トークンを何秒間ホールドしたか」を 1 件ずつ表すレコード
HoldStat	holder_id, weighted_score	特定ホルダーが累積で何秒（重み付き）保有したかのスナップショット
pydantic.BaseModel を継承しているため 型安全 & バリデーション が自動化。

2. 取り込み層 — api/grpc_server.py
Record : 単発イベント (HoldMsg) を受信して AsyncTracker.record() へ流す
Broadcast : 双方向ストリーム。大量の HoldMsg を一括送信可能
Stats : 現在のスナップショットをストリームで返す（単一 or watch も可）
非同期 (grpc.aio) 実装 のためクライアントからの大量同時送信でもスレッドを消費せずスケール。

3. 集計バッファ — tracker.py
AsyncTracker.record(event)
受け取った HoldEvent を メモリ内の Dict<(token, holder), List[Event]> へ追加

snapshot()
すべてのイベントを走査し、終了済み (end!=None) のみを対象に
score = (end‑start) [sec] × weight を合算 → List[HoldStat] で返却
gRPC → Tracker → Storage の間に挟むことで「リアルタイム集計」と「永続化」を分離。

4. スコア計算 — calculator.py
メソッド	概要
calculate_score(events)	同一ホルダーのイベント配列から重み付きスコアを算出
merge_overlaps(events)	期間が重複するイベントをマージし二重加算を防止

5. 永続化 — storage/mongodb.py
Motor (async) で本番 MongoDB に書き込み
接続失敗時は mongomock へ自動フォールバック → CI でも DB 不要
save_event() : HoldEvent → BSON へ変換して挿入
get_stats() : Mongo の $group 集計でサーバ側計算（大量データでも高速）
{"$project": {
    "duration_s": { "$divide": [{ "$subtract": ["$end", "$start"]}, 1000.0]},
    "weight": 1}}
WiredTiger の差分計算を利用するため Python 側でループするより高速。

6. スケジューラ — scheduler.py
AsyncScheduler.every(interval, coro)
任意コルーチンを指定間隔で起動（メトリクスの定期 flush などに使用可）
run_forever()
asyncio.create_task() でジョブを張り付け、Ctrl‑C で優雅にシャットダウン

7. CLI エントリ ― app_holdmetrics.py
python -m poh_holdmetrics.app_holdmetrics grpc  # gRPC サーバ起動
python -m poh_holdmetrics.app_holdmetrics worker  # バックグラウンド集計 & flush
引数に応じて asyncio.run() で上記コンポーネントを組み合わせて起動できるようにラップ。

8. プロトコル — protocols/hold.proto
service HoldMetrics {
  rpc Broadcast (stream HoldMsg) returns (stream HoldAck);
  rpc Record    (HoldMsg)        returns (HoldAck);
  rpc Stats     (google.protobuf.Empty) returns (stream HoldStat);
}
protoc 実行済み生成物 (*_pb2.py) をリポジトリにコミットしているため
利用側は protoc 不要。

9. テストスイート — tests/
pytest-asyncio で 非同期 API をそのままテスト
test_storage.py
ローカル mongod が立っていれば実 DB、無ければ mongomock に自動スキップ (xfail)
coverage 設定済み (pytest --cov) → CI で品質ゲート可能

10. 開発フローの一例
・ 編集しながら即反映
pip install -e ".[api,test]"

・ gRPC サーバ起動（実データ投入）
python -m poh_holdmetrics.app_holdmetrics grpc

・ MongoDB の内容を確認
mongosh --eval 'db.hold_events.find().pretty()'

# 単体テスト & 型チェック
pytest -q
mypy poh_holdmetrics_python
まとめ
エンドポイント: gRPC (asyncio)
リアルタイム集計: AsyncTracker (in‑mem)
バッチ／履歴分析: MongoDB $group パイプライン
安全な配布: python -m build → dist/*.whl
CI/ローカル: mongomock で DB 依存ゼロ
全部 async/await 対応 — gRPC 受信〜DB 書き込みまでブロッキング無し
この構成で「Web3 トークンの ホールド時間スコア をリアルタイム算出しつつ永続化」するパイプラインを軽量に実現しています。


#　mongodb.pyについて
使い方と効果
| シナリオ                          | `MONGODB_URL`               | 結果                             |
| ----------------------------- | --------------------------- | ------------------------------ |
| **CI / ローカルテスト**（クラウド DNS 不通） | そのまま `mongodb+srv://…`      | 自動で `mongomock` に切替 → **テスト緑** |
| **開発 PC**（自前 mongod 起動中）      | `mongodb://localhost:27017` | 本物の MongoDB に書込                |
| **本番**（Atlas など）              | `mongodb+srv://user:pass@…` | 正常接続し実 DB へ書込                  |

注意 : フォールバックを使う場合は
pip install mongomock  (または Poetry の dev-dependencies) を忘れずに！


変更ポイントまとめ
| 旧実装                                              | 新実装                                                              |

| `config.settings` に依存し AttributeError が出ていた      | 内部 `_Settings` で `.env` / 環境変数を直接読み込みつつ、`config.settings` があれば優先 |
| 同期的に `motor.motor_asyncio.AsyncIOMotorClient` 生成 | 変わらず。ただし `tz_aware=True`・`serverSelectionTimeoutMS=5000` を付与     |
| Datetime のタイムゾーン未指定時にエラーの可能性                  | すべて UTC に補正                                                      |
| インデックスなし                                         | 起動直後に自動で index を張る                                               |
| `purge()` のみユーティリティ                              | `close()` も追加（FastAPI lifespan 等で利用可）                            |
| テスト失敗要因だった `settings.mongodb_url` 欠損             | 本ファイル単体で解決（環境変数ベース）                                              |

これで 実際の MongoDB クラスタ を使った保存／集計がそのまま動き、
以前のテスト (pytest) もパスする構成になります。


# hold_pb2_grpc.pyの自動生成
cd D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python

python -m grpc_tools.protoc ^
  --proto_path=poh_holdmetrics/protocols ^
  --python_out=poh_holdmetrics/protocols ^
  --grpc_python_out=poh_holdmetrics/protocols ^
  poh_holdmetrics/protocols/hold.proto


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
sudo apt install -y protobuf-compiler
sudo apt install python3.12-dev

これでシステムに
/usr/lib/x86_64-linux-gnu/libpython3.12.so
/usr/include/python3.12/…
といったファイルが入ります。
python3.12 コマンドで起動できるようになります。

# pip と仮想環境の準備
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.12
python3.12 -m venv ~/envs/linux-dev
source ~/envs/linux-dev/bin/activate

2. プロジェクトをクローン／マウント
Windows 上のソースコードディレクトリ
たとえば D:\city_chain_project\DAGs\libs\algorithm\ 配下にあるなら、WSL 側からは
/mnt/d/city_chain_project/DAGs/libs/algorithm/ でアクセスできます。
下記のようになればOK
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_holdmetrics

2. Cargo に「Python をリンクしてね」と教えてあげる
② PyO3 に正しい Python を教える
もし python3.12 を明示したい場合：
export PYTHON_SYS_EXECUTABLE=$(which python3.12)

# 依存を入れる
pip install "motor[asyncio]"

editable インストールを更新
プロジェクト直下 ( pyproject.toml があるディレクトリ ) で
pip install -e .

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
cd ../poh_holdmetrics
pip install -e '.[test]'
#　wheel を dist\ に置きたいなら comandプロンプトから（ややこしいね。。）
pip install -e .

python -m pip install --upgrade build   # 必須
python -m pip install --upgrade twine  # PyPI に上げるなら
python -m build             # ← wheel と sdist の両方を生成


# テストには、2つのサーバーを起動する必要がある。Mongodb,grpc
 それゆえ、両方を立ち上げておく必要がある。
# 単体でgrpc起動
pip install --no-cache-dir "protobuf==5.29.2" "grpcio==1.74.0" "googleapis-common-protos>=1.65,<2" fastapi uvicorn click pydantic-settings

set GRPC_ADDRESS=127.0.0.1:60051
python -m poh_holdmetrics.app_holdmetrics grpc

これで HoldMetricsStub.Stats() が正しく呼び出せ、
pytest の test_grpc_stats_broadcast はエラーなく通るようになります。

#　Windows cmdを別に起動してgrpcの起動チェック
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python>python -X dev -c "import grpc,poh_holdmetrics.protocols.hold_pb2 as pb,poh_holdmetrics.protocols.hold_pb2_grpc as api; ch=grpc.insecure_channel('127.0.0.1:60061'); stub=api.HoldMetricsStub(ch); it=stub.Stats(pb.google_dot_protobuf_dot_empty__pb2.Empty()); first=next(it); print('OK holder_id=', first.holder_id, 'score=', first.weighted_score)"

OK holder_id=  score= 0.0　とでればいい。

つぎは、非同期でのgrpcのチェックをcheck_grpc.pyを使ってチェックする
(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\api>python check_grpc.py

OK holder_id=  score= 0.0　とでればいい。

#　linux でgrpcの起動
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python$ python -m poh_holdmetrics.app_holdmetrics grpc
INFO:poh_holdmetrics.api.grpc_server:gRPC server started on 0.0.0.0:60051
と起動メッセージを吐いて常駐したので gRPC スタブがバインドされ、Stats RPC も受け付ける状態 になっています。あとはクライアント側（テストスクリプトや grpcurl 等）から次のように呼び出せば動作確認できます。

#　Windowsで　HTTpサーバー軌道
2) 別ターミナルで HTTP サーバ起動
同じ仮想環境を有効化：
D:\city_chain_project\.venv312\Scripts\activate
cd D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python

余計な環境変数はクリア（以前の protobuf/GIL 問題の回避）：
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION_VERSION=

Rust拡張を使わないなら（安定目的）：
set POH_DISABLE_RUST=1

HTTP の bind を設定（必要なら）：
set HTTP_HOST=127.0.0.1
set HTTP_PORT=8000
set LOG_LEVEL=DEBUG

起動（※ app_holdmetrics.py を遅延インポート版にしてある前提）：
python -m poh_holdmetrics.app_holdmetrics http

期待ログ：
INFO:     Uvicorn running on http://127.0.0.1:8000


# Wsl側から、mongod をローカルで起動
# 変数にパスを入れておく（打ち間違い防止）
mkdir -p /home/satoshi/work/city_chain_project/network/DB/mongodb/data
chmod 700 /home/satoshi/work/city_chain_project/network/DB/mongodb/data

今の ~/mongo/mongod.conf をこう直せば動きます
mkdir -p ~/mongo
cat > ~/mongo/mongod.conf <<'EOF'
storage:
  dbPath: /home/satoshi/work/city_chain_project/network/DB/mongodb/data

net:
  bindIp: 127.0.0.1
  port: 27017

processManagement:
  fork: false
EOF

#　そして、起動は下記
mongod --config ~/mongo/mongod.conf

set "OLDPATH=%PATH%"
set "PATH=%VIRTUAL_ENV%\Scripts;%SystemRoot%\System32;%SystemRoot%"
pytest -vv -s poh_holdmetrics/tests/test_storage.py
set "PATH=%OLDPATH%"
これで確認できる。

# WSL側から mongod を動かす（最も楽）
公式 tarball を展開
cd ~
wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2204-7.0.14.tgz
tar xf mongodb-linux-x86_64-ubuntu2204-7.0.14.tgz

sudo mv mongodb-linux-x86_64-ubuntu2204-7.0.14/bin/* /usr/local/bin/

そして、Ubuntu 24.04 (noble) 用 apt レポジトリはまだ無いので tarball が安全。
データディレクトリ作成 & 起動
sudo mkdir -p /opt/mongodb/7.0.14
sudo tar xf mongodb-linux-x86_64-ubuntu2204-7.0.14.tgz -C /opt/mongodb/7.0.14 --strip-components=1
sudo ln -s /opt/mongodb/7.0.14/bin/* /usr/local/bin/

■　パターンB：WSL(Ubuntu)に Linux版 mongod を入れてWSL内で起動（おすすめ）
Windowsとは独立した高速なMongoをWSL内に持てる。DBはLinux側に置こう（例：~/mongo-data）。
# 1) MongoDBをWSLにインストール（簡易手順・systemdなしでもOK）
sudo apt update
sudo apt install -y mongodb # これで入るディストリもあるけど、無ければ "mongodb-org" の公式リポ手順を使う

# 2) データ置き場（Linux側）を作成
mkdir -p ~/mongo-data

# 3) フォアグラウンドでまず起動確認（Ctrl+Cで止められる）
mongod --dbpath ~/mongo-data --port 27017 --bind_ip 127.0.0.1

# 4) 常駐させたいなら（fork + ログ出力）
sudo mongod --dbpath ~/mongo-data --port 27017 --bind_ip 127.0.0.1 \
  --fork --logpath ~/mongo-data/mongod.log

動作確認：
# mongosh が無ければ: sudo apt install -y mongodb-mongosh
echo 'db.runCommand({ping:1})' | mongosh --quiet mongodb://127.0.0.1:27017

テスト：
source ~/envs/linux-dev/bin/activate
pytest -vv -s DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python/poh_holdmetrics/tests/test_storage.py

systemd が有効なWSLなら sudo systemctl start mongod / enable mongod も使えるよ。

■パターンC：DockerでMongo（いちばん手軽）
あなたの環境はDocker整ってるから、これが一番楽かも。
# 初回だけ：永続ボリューム作成
docker volume create mongo-data

# 起動
docker run -d --name mongo \
  -p 27017:27017 \
  -v mongo-data:/data/db \
  mongo:6.0

すぐ確認するコマンド
# 1) ログを見る（起動時の「waiting... started successfully」や接続ログが出てるはず）
tail -n 50 ~/mongo-data/mongod.log

# 2) プロセスとポート
pgrep -af mongod
sudo ss -ltnp | grep 27017

テスト側：MONGODB_URL=mongodb://127.0.0.1:27017 で普通に接続。


#　念のためのワンコマ確認：
パワーシェルを立ち上げて、poh_metrics_python\から下記をやってみて。
・HTTP ヘルスチェック
curl http://127.0.0.1:8000/healthz
もしくはブラウザで http://127.0.0.1:8000/docs が開けばOK。

・Mongo ポート疎通
powershell -Command "Test-NetConnection -ComputerName 127.0.0.1 -Port 27017"
（mongosh があれば mongosh --eval "db.runCommand({ping:1})" でもOK）


✅  テスト環境から接続確認
Python 側で接続できるか確認：
python -c "
import pymongo
client = pymongo.MongoClient('mongodb://localhost:27017')
print(client.admin.command('ping'))
"
結果例：
{'ok': 1.0}
が出れば OK。

先に Rust拡張 を入れる（これが無いと poh_holdmetrics_python の依存解決で転ぶ）
# レポジトリ ルートで
maturin develop \
  -m DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_rust/Cargo.toml \
  --features python \
  --release

1. pytest で統合テスト（推奨）
別シェルを開いて
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python$ pytest poh_holdmetrics/tests/test_api.py::test_grpc_stats_broadcast -q
.                                                                                                        [100%]
1 passed in 2.03s

2. grpcurl ワンライナーで手動確認
# いまのカレントが poh_holdmetrics_python/ でも /mnt/d/... でも動くよう絶対パス版
grpcurl -plaintext \
  -import-path /mnt/d/city_chain_project/DAGs/libs/algorithm/poh_holdmetrics/poh_holdmetrics_python/poh_holdmetrics/protocols \
  -proto hold.proto \
  -d '{}' 127.0.0.1:60051 poh.HoldMetrics/Stats
レスポンス例
{
  "holderId": "h",
  "totalSeconds": "5",
  "weightedScore": 10,
  "updatedAt": {
    "seconds": 1721572980,
    "nanos": 0
  }
}

3. 運用時の覚え書き
項目	値	備考
gRPC Listen Address	0.0.0.0:60051	.env の GRPC_ADDRESS で変更
RPC 実装	Broadcast / Record / Stats	GetSnapshot も必要なら追加可
認証・TLS	現状なし（開発用）	運用では grpc.aio.server(credentials=...)

#　総合テストはWSL から
python -m pytest poh_holdmetrics/tests


# mongodbに非同期で書き込んでる？
はい、非同期（async / await）対応しています。ポイントだけかいつまむと――
| 箇所                                                 | 何をしているか                                                                                               | どこが “非同期” か                                                     |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `motor.motor_asyncio.AsyncIOMotorClient` でクライアント生成 | Motor は公式の “async 版 PyMongo” ライブラリ。内部で `pymongo` をスレッドプールに流さず、**純粋に asyncio のコルーチン**としてソケット I/O を扱います | `await collection.insert_one(...)` などが **イベントループをブロックしない**      |
| `save_event()`                                     | `await self._col.insert_one(doc)`                                                                     | 挿入完了まで他タスクが並列に走れる                                               |
| `get_stats()`                                      | `cursor = self._col.aggregate(pipeline)`<br>`async for doc in cursor:`                                | aggregation の結果を **ストリームで受け取りながら**逐次 yield されるので、大量結果でもメモリ効率が良い |
| インデックス作成                                           | `asyncio.create_task(self._ensure_indexes())`                                                         | 起動直後に **バックグラウンドタスク**として fire‑and‑forget。メインの処理を待たせない           |


実際の同時実行イメージ
┌──────── event‑loop ────────┐
│ Task‑A: await save_event   │ ← 書き込み I/O 待ちの間に…
│ Task‑B: await get_stats    │ ← 別タスクも進行
│ Task‑C: other async stuff  │
└───────────────────────────┘
フォールバック時
mongomock へ切り替わった場合は純粋なメモリ実装です
（I/O が無いので “非同期” かどうかは実質関係なく、とても速い）。
ラッパークラス _AsyncMock が await をそのまま通しているので
コールサイトは同じ await XXX で書けます。

「motor ってスレッドプールで裏側が同期 I/O なの？」
いいえ。Motor は libuv などは使わず Python の asyncio ソケットを直に扱います。Low‑level で loop.sock_connect / sock_recv を呼び出しているため、スレッドを増やさずに多量の同時接続をさばける設計になっています。

まとめ
Motor クライアント + await により MongoDB との通信は完全非同期。
テストや CI でサーバが無い場合は mongomock へ自動フォールバックし、同じ async API で動く。
そのため 本番環境でもテスト環境でも同じコードで非同期 I/O が確保されています。


これでひと通り gRPC 経由の保持イベント登録と Stats ストリーム取得 が可能になっています。もし追加で
TLS 化
認証（API キーや mTLS）
GetSnapshot のページング
などが必要になったら教えてください。


(.venv312) D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python>pytest -vv -s
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python
configfile: pyproject.toml
testpaths: poh_holdmetrics/tests
plugins: anyio-4.9.0, asyncio-1.0.0, cov-6.2.1
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 16 items

poh_holdmetrics/tests/test_api.py::test_http_hold_and_stats PASSED
poh_holdmetrics/tests/test_api.py::test_grpc_stats_broadcast PASSED
poh_holdmetrics/tests/test_calculator.py::test_calculate_score_zero <- ..\..\..\..\..\..\mnt\d\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_calculator.py PASSED
poh_holdmetrics/tests/test_calculator.py::test_calculate_score_multiple <- ..\..\..\..\..\..\mnt\d\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_calculator.py PASSED
poh_holdmetrics/tests/test_rust_bindings.py::test_calculate_score_basic PASSED
poh_holdmetrics/tests/test_rust_bindings.py::test_aggregator_record_and_snapshot PASSED
poh_holdmetrics/tests/test_rust_bindings.py::test_rust_extension_imports PASSED
poh_holdmetrics/tests/test_rust_bindings.py::test_rust_vs_python_single_case PASSED
poh_holdmetrics/tests/test_rust_bindings.py::test_rust_vs_python_param[0.0-1.0] PASSED
poh_holdmetrics/tests/test_rust_bindings.py::test_rust_vs_python_param[1.0-1.0] PASSED
poh_holdmetrics/tests/test_rust_bindings.py::test_rust_vs_python_param[2.5-0.5] PASSED
poh_holdmetrics/tests/test_rust_bindings.py::test_rust_vs_python_param[10.0-3.0] PASSED
poh_holdmetrics/tests/test_rust_bindings.py::test_rust_vs_python_param[1234.567-0.01] PASSED
poh_holdmetrics/tests/test_scheduler.py::test_scheduler_start_stop <- ..\..\..\..\..\..\mnt\d\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_scheduler.py PASSED
poh_holdmetrics/tests/test_storage.py::test_mongo_storage_integration PASSED
poh_holdmetrics/tests/test_tracker.py::test_tracker_basic <- ..\..\..\..\..\..\mnt\d\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_tracker.py PASSED