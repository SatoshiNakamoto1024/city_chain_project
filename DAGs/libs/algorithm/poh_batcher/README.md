poh_batcher (1) – ACK バッチ圧縮
1. リポジトリツリー
poh_batcher/
├── LICENSE                       # Apache‑2.0 など
├── README.md                     # 使い方・仕様
├── .gitignore                    # __pycache__ / dist / .env など
├── pyproject.toml                # [project] + build-system = "hatchling"
└── poh_batcher/
    ├── __init__.py
    ├── types.py                  # BatchHeader / PackedBatch dataclass
    ├── compression.py            # Zstd ↔ Gzip ラッパ
    ├── storage.py                # (任意) ローカル FS / S3 / GCS adapter
    ├── batcher.py                # AsyncBatcher (核心)
    ├── cli.py                    # `poh‑batcher` エンドポイント
    └── tests/
        ├── __init__.py
        ├── test_compression.py
        ├── test_batcher.py
        └── test_cli.py
依存: pydantic>=2.0, poh-ack>=0.1.0, zstandard>=0.22 (optional), rich (CLI), pytest‑asyncio (dev)

以下、poh_batcher の主要機能と構成を項目ごとに詳しく解説します。
1. 概要
poh_batcher は、Proof-of-History（PoH）チェーンの ACK（承認応答）を 非同期バッチ圧縮 し、ファイルシステム（または S3）へ順次出力するライブラリ＆ CLI ツールです。
高スループットかつ低レイテンシで多数の ACK を集約し、バックエンドへの書き込みコストを削減します。

入力：poh_ack.models.AckRequest（1 ACK = JSON 1 行）
出力：日付階層＋シーケンシャル命名のファイル（.json, .json.gz, .json.zst）
圧縮：gzip（標準）／Zstandard（zstandard がインストール済みなら自動選択）
保存先：ローカル FS (file://…) or S3 (s3://bucket/prefix)

2. 主要コンポーネント
ファイル	役割
compression.py	バイナリデータの圧縮／伸張ロジック
storage.py	ファイル／S3 への非同期保存インターフェイス
types.py	Pydantic モデル定義（BatchHeader, PackedBatch, AckItem）
batcher.py	非同期バッチ処理コア（AsyncBatcher + Batcher）
cli.py	Click ベースの CLI エントリポイント
tests/	各モジュールの単体テスト

2.1 compression.py
compress(data: bytes, level: int) -> (codec: str, compressed: bytes)
Zstandard（zstd パッケージ）利用可能なら "zstd"、そうでなければ "gzip"
decompress(codec: str, data: bytes) -> bytes
ヘッダ文字列に応じた逆圧縮

2.2 storage.py
抽象基底：StorageBackend
save_json(key: str, text: str)
exists(key: str) -> bool
get_url(key: str) -> str

実装：
LocalStorage (file://…)
path.write_text() を run_in_executor で非同期呼び出し
S3Storage (s3://bucket/prefix)
boto3 / 任意で aioboto3 サポート
put_object, head_object をラップ

ユーティリティ：
storage_from_url(url: str) で URL 文字列に応じたバックエンドを返す

2.3 types.py
Pydantic v2 モデル群（JSON⇔Python オブジェクト変換）：
AckItem
id, timestamp, signature, pubkey

BatchHeader
count: int （件数）
compression: Literal["gzip","zstd"]

PackedBatch
header: BatchHeader
payload: bytes （圧縮済バイナリ）

2.4 batcher.py
AsyncBatcher
非同期バッチャのコア実装：
初期化
AsyncBatcher(
    max_items: int = 256,
    timeout: float = 0.5,
    sink: Callable[[PackedBatch], Awaitable[None]],
)

max_items: １バッチの最大件数
timeout: 最初の ACK 受信から秒数経過で強制フラッシュ
sink: フラッシュ時に呼ばれる非同期コールバック（PackedBatch 引数）

ライフサイクル
await batcher.start()   # バックグラウンド task 開始
await batcher.enqueue(ack_item)
await batcher.stop()    # キューをドレインして flush →停止

内部ワーカー
キュー取得（asyncio.Queue.get() + タイムアウト）
buf に溜め込み
len(buf)>=max_items OR timeout 経過 OR stop() 呼び出し → pack_acks → sink(batch)

後方互換
Batcher = AsyncBatcher
pack_acks / unpack_batch
pack_acks(list[AckRequest]) -> PackedBatch

JSON ミニファイ → 圧縮 → PackedBatch(header,payload)
unpack_batch(batch: PackedBatch) -> list[AckRequest]
伸張 → JSON パース → AckRequest モデル化

2.5 cli.py
Click ベースの CLI：
$ cat acks.jsonl | poh-batcher --batch-size 500 --batch-timeout 2.0 --output-dir file:///tmp/batches

オプション
-n, --batch-size: 一度にまとめる最大件数
-t, --batch-timeout: 一括 flush までの秒数
-o, --output-dir: file://… or s3://…

動作
AsyncBatcher(batch_size, timeout, sink=storage.save_json) を生成
start() → 標準入力から１行ずつ読み込み
JSON デコード＋モデル検証 → submit(ack)
KeyboardInterrupt / EOF で stop()

出力フォーマット
YYYYMMDD/HH/ack_batch_<seq>.json(.gz|.zst)
フォルダ階層で日付＋時間を分割
連番 <seq> で重複回避

3. ワークフロー例
from poh_batcher.batcher import AsyncBatcher
from poh_batcher.storage import LocalStorage
from poh_batcher.types import PackedBatch
import asyncio, json

async def print_sink(batch: PackedBatch):
    print("batch:", batch.header.count, batch.header.compression)
    # 中身を確認
    raw = batch.payload
    if batch.header.compression=="gzip":
        import gzip; raw = gzip.decompress(raw)
    items = json.loads(raw)
    print(items)

async def main():
    sink = print_sink
    batcher = AsyncBatcher(max_items=4, timeout=1.0, sink=sink)
    await batcher.start()
    for i in range(10):
        # たとえば poh_ack.models.AckRequest インスタンスを使う
        ack = AckItem(id=str(i), timestamp="2099-01-01T00:00:00Z", signature="", pubkey="")
        await batcher.enqueue(ack)
    await asyncio.sleep(1.1)  # timeout 待ち
    await batcher.stop()

asyncio.run(main())

4. 設計上のポイント
非同期／バックプレッシャ
asyncio.Queue + wait_for によるタイムアウトで、I/O ボトルネック抑制。

プラガブルな保存先
ストレージは抽象化。ローカル→S3→将来は GCS, Azure も追加可能。

圧縮フォールバック
Zstandard があれば高速 zstd、なければ標準 gzip。

日付階層＋シーケンス命名
バッチファイルが永続的に大量増えても管理しやすい。

後方互換
旧コードとの互換性を保つ Batcher エイリアス。

以上が poh_batcher の詳細な機能解説です。疑問点やさらに掘り下げたい部分があればお知らせください！


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
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_batcher$


# ※poh_ack_rust 側を調整しないとimport上手くできない。
# walkdirをつかう
こちらが tests/test_py_bindings.rs の “本番実装用” 完全版です。
walkdir を使ってビルド済みの cdylib（および Windows は pyd）を自動検出し、
PYTHONPATH にディレクトリを設定してからインポートを行います。

dev-dependencies 追記
Cargo.toml の [dev-dependencies] セクションに以下を入れてください。
[dev-dependencies]
walkdir = "2.5"
pyo3    = { version = "0.25", default-features = false, features = ["extension-module", "abi3-py312"] }

これで cargo test （Rust 側テスト）と、
その後の maturin develop --release ＋ pytest（Python 側テスト）を安定して共存できます。

#　ポイント
target\debug\ or target\release\ の中にある poh_ack_rust.dll を同じディレクトリに poh_ack_rust.pyd としてコピーします。.pyd は Python が Windows 上で拡張モジュールとみなす拡張子です。

Cargo.toml の [features] セクションをこう変更すると、cargo build／cargo test が常に Python 拡張モジュール付きでビルドされます。
 [features]
# ── デフォルト: Rust + Python拡張 ───────────────────
default = ["core", "py-ext"]

 # Python拡張ONビルド
 py-ext = ["pyo3/extension-module", "pyo3/abi3-py312", "pyo3/auto-initialize"]

使い方確認
cargo clean
cargo build --features py-ext   # 本物 DLL を生成
  ※この意味で上記必要→　--features py-ext makes Cargo build the cdylib with #[pymodule] symbols
cargo test --features python -- --test-threads=1            # もう ImportError は出ない

ポイント:
panic! の {debug,release} → {{debug,release}} でコンパイルエラー解消。
本物 DLL（target\debug\poh_ack_rust.dll など）を優先的に拾う。
それでも足りない場合は deps も見るので昔のパスも OK。
これで smoke テストが通ります。

PyInit_* が入らない DLL が出来る理由
ビルド手順,	生成物,	PyInit_* が入る?	用途
cargo build / cargo test（debug）,	target/debug/<hash>.dll,	❌ ただのリンク用	Rust テスト実行用
cargo build --release,	target/release/<hash>.dll,	❌ 同上	最適化済みリンク用
cargo build --features py-ext,	target/debug/poh_ack_rust.dll,	✅ Python用だが拡張子は dll	欲しいのはこれ
maturin develop --release,	target/wheels/.../poh_ack_rust-*.pyd 等,	✅ Python用（pyd/so）	pip インス
これらをcd poh_ack_rustで済みである前提で下記をやる。

# poh_ack をimport
cd poh_ack
　※プロジェクトの test extras をまとめて拾ってくる
pip install -e '.[test]'
python -m pytest poh_batcher/tests
