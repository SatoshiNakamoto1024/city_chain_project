poh_ack/
├── README.md
├── LICENSE                         # → Apache‑2.0 などを配置
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml                  # Rust→maturin→pytest 一気通し CI
│
├── poh_ack_rust/                   # Rust コア & PyO3 バインディング
│   ├── Cargo.toml
│   ├── pyproject.toml              # maturin build 設定（abi3‑py312）
│   ├── build.rs
│   ├── benches/
│   │   └── bench_verifier.rs
│   ├── src/
│   │   ├── lib.rs
│   │   ├── ackset.rs
│   │   ├── main_ack.rs
│   │   ├── verifier.rs            # 署名・TTL 検証ロジック
│   │   ├── ttl.rs                 # TTL helper
│   │   ├── error.rs
│   │   └── bindings.rs            # #[pymodule] & #[pyfunction]
│   └── tests/
│       ├── test_cli.rs
│       ├── test_ackset.rs
│       ├── test_verifier.rs
│       └── test_py_bindings.rs
│
└── poh_ack_python/                 # Python ラッパ & ユーティリティ
    ├── pyproject.toml              # Hatch(PEP‑621) でビルド
    ├── README.md
    └── poh_ack/
        ├── __init__.py
        ├── _version.py
        ├── cli.py                  # エンドポイント
        ├── models.py               # Pydantic v2: AckRequest / AckResult
        ├── verifier.py             # async FFI + フォールバック pure‑py
        └── tests/
            ├── __init__.py
            ├── test_verifier.py
            └── test_ttl.py

📑 src/error.rs：AckError 列挙型
・デコード／シリアライズエラー
DecodeBase58, InvalidJson

・鍵・署名フォーマット関連
InvalidKeyLength, InvalidSignatureLength
InvalidSignature, InvalidPublicKey

・検証失敗
SignatureVerification, TtlExpired

・重複
DuplicateId

・IO／内部エラー
Io, InternalError

thiserror マクロで人間可読なメッセージを一元管理し、エラー→Python例外への変換も容易に。

⏱️ src/ttl.rs：validate_ttl
pub fn validate_ttl(ts: &DateTime<Utc>, ttl_seconds: i64) -> Result<(), AckError> {
    let now = Utc::now();
    if *ts + Duration::seconds(ttl_seconds) < now {
        Err(AckError::TtlExpired(ts.to_rfc3339()))
    } else {
        Ok(())
    }
}

ts + ttl_seconds と現在時刻を比較
有効期限切れなら TtlExpired エラー

🤝 src/ackset.rs：Ack ＆ AckSet
■　struct Ack
・フィールド：id: String、timestamp: DateTime<Utc>、signature: String、pubkey: String
・from_json(&str) -> Result<Ack, AckError>
・canonical_payload() -> String
・verify_signature
　　Base58→バイト列デコード
　　ed25519_dalek::VerifyingKey で署名検証
・verify_ttl
　　TTL のみチェック
・verify
　　署名＋TTL を一括検証
・verify_async
　　tokio::task::spawn_blocking で非同期ラップ

■　struct AckSet
・内部に Vec<Ack> を保持
・new()
・add(&mut, Ack, ttl)
　　重複IDチェック → verify → push
・add_async
　　spawn_blocking でまず検証 → メインスレッドで重複チェック＆追加
・add_batch_async
　　イテレータで順次 add_async
・ids(), len(), is_empty(), clear()
　　同期・非同期 API が揃っており、BFT やネットワーク層と並行して安全に使えます。

🔍 src/verifier.rs：ファイル／文字列一括検証
verify_ack_json(json_str, ttl) -> Future<String>
JSON→Ack → spawn_blocking で Ack::verify → 成功なら ID
verify_ack_file(path, ttl) -> Future<Vec<String>>
非同期ファイル読み込み → JSON 配列としてパース
AckSet::new() で一件ずつ add → IDリスト返却
CLI用途やバッチジョブに便利な高レベル関数です。

🐍 src/bindings.rs：PyO3 バインディング
例外変換
impl From<AckError> for PyErr → 全部 PyValueError に
#[pyclass] PyAck

__new__(id, timestamp, signature, pubkey)

.verify(ttl) / .verify_async(ttl)（Python awaitable）

.id, .timestamp getter

#[pyclass] PyAckSet

__new__() → 空集合
.add(ack, ttl) / .add_async(ack, ttl)

.ids()

#[pyfunction] check_ttl(ts, ttl) -> bool

→ Python から import poh_ack_rust するだけで、同期・非同期検証クラスがそのまま使えます。

🏃‍♂️ src/main_ack.rs：CLI バイナリ
clap::Parser で --input <file> / --ttl <seconds> 引数
ファイル読み込み → serde_json::from_str::<Ack> → ack.verify(ttl)
成功時に "ACK '<id>' is valid and within <ttl> seconds TTL" 出力
シンプルなスタンドアロンツールとしても運用可能です。

⚙️ src/lib.rs：エクスポート
pub mod ackset;
pub mod ttl;
pub mod error;
pub use ackset::{Ack, AckSet};
pub use ttl::validate_ttl;
pub use error::AckError;

#[cfg(feature = "python")]
pub mod bindings;
Rust コア部分は Ack / AckSet / validate_ttl / AckError をそのまま公開
python feature でバインディングをまとめて登録

⚡ ベンチマーク & テスト
benches/bench_verifier.rs
Criterion で verify_signature＋verify_ttl の p99 を計測
tests/
test_ackset.rs：同期／非同期 add / 重複 / TTL エラー
test_verifier.rs：verify_ack_json / verify_ack_file の正常・異常
test_cli.rs：実際に main_ack バイナリを呼び出す統合テスト
test_py_bindings.rs：pyo3::prepare_freethreaded_python() 経由で FFI smoketest
これらすべてが cargo test --release --features python で一発パスします。

🎯 まとめ
Core：ed25519-dalek＋chrono＋serde で安全・高速な検証
Concurrency：tokio::spawn_blocking を使った非同期サポート
FFI：PyO3(0.25)＋pyo3-async-runtimes(0.25) で Python へ丸投げ可能
CLI：clap(4.x) でスタンドアロンツール提供
Quality：ベンチ/単体/統合/FFI テスト網羅
poh_ack_rust は、PoH‑ACK の署名＋TTL検証を高い性能と信頼性で提供する完全実装コアです。



#　注意ポイント
| 問題だった点                          | 修正内容                                                                            |
| ------------------------------- | ------------------------------------------------------------------------------- |
| **Tokio runtime の Builder が不要** | async‑runtimes が内部で組み立てるので import を削除                                           |
| **`future_into_py` 戻り値型**       | 0.25 系は **`Bound<'py, PyAny>`** を返す → 署名も `PyResult<Bound<'py, PyAny>>` に変更     |
| **`Ok(())` の扱い**                | `()` は `IntoPy<PyObject>` 実装済み → Python では `None` になる                           |
| **PyModule API**                  | 0.25 系では GIL バインド済み `Bound<'_, PyModule>` が推奨 (`add_class` / `add_function` あり) |

これで 型不整合 (E0308) と メソッド未検出 (E0599) は解消され、
maturin develop --release が通ります。

# 注意！！
以下の　か所だけ修正 すれば衝突が解消します。
（Rust 側 wheel の配布名を “poh‑ack‑rust” に変えるだけ。モジュール名 import poh_ack_rust はそのまま使えます）
① poh_ack_rust/pyproject.toml
-[project]
-name = "poh-ack"
+[project]
+# -------------------------------
+# PyPI / pip 上の Distribution 名
+# -------------------------------
+name = "poh-ack-rust"   # ★ここを変更★
ほかのフィールド（version / description / classifiers …）はそのままで OK。


# TEST　について
下記のtest_py_bindings.rsの
#[test]
fn python_bindings_smoke() {
この部分で、エラーが止まらない。苦しむ。。

---- python_bindings_smoke stdout ----
thread 'python_bindings_smoke' panicked at tests\test_py_bindings.rs:55:43:
import failed: PyErr { type: <class 'ImportError'>, value: ImportError('dynamic module does not define module export function (PyInit_poh_ack_rust)'), traceback: None }
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
failures:
    python_bindings_smoke
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 10.55s
error: test failed, to rerun pass `--test test_py_bindings`

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


🔧 実行方法
# release ビルド + Criterion ベンチを実行
cargo bench --bench bench_verifier

補足
Ack::verify(ttl_sec) が Result<(), AckError> を返すため、
ベンチ内では unwrap() で必ず成功することを確認します。

once_cell::sync::Lazy でサンプル Ack を 1 度だけ作成し、
毎イテレーションで同じ値を使うことでキー生成コストを除外しています。

Criterion の default 設定（統計試行回数・ウォームアップ等）は
そのまま使用しています。必要に応じて Criterion::default().warm_up_time(...)
などで調整してください。

これで async‑runtimes 0.25 系 / PyO3 0.25 系 環境でも
署名 + TTL を含む Ack::verify のスループットを正しく測定できます。


# テスト
maturin develop --release
そして、.pydへコピー
cargo test --features python -- --test-threads=1 
そうすると、

    Finished `bench` profile [optimized] target(s) in 11.38s
     Running benches\bench_verifier.rs (target\release\deps\bench_verifier-679e0abb822e781b.exe)
Gnuplot not found, using plotters backend
Ack::verify             time:   [82.836 µs 90.155 µs 97.378 µs]
Found 2 outliers among 100 measurements (2.00%)
  2 (2.00%) high mild


    Finished `test` profile [unoptimized + debuginfo] target(s) in 1m 48s
     Running unittests src\lib.rs (target\debug\deps\poh_ack_rust-e3d23a5c167e6fe3.exe)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src\main_ack.rs (target\debug\deps\main_ack-f478451610a45353.exe)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests\test_ackset.rs (target\debug\deps\test_ackset-c2114affb359c344.exe)

running 5 tests
test add_and_ids_sync ... ok
test add_async_and_batch ... ok
test add_async_duplicate ... ok
test add_duplicate_sync ... ok
test ttl_error_sync ... ok

test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.23s

     Running tests\test_cli.rs (target\debug\deps\test_cli-6021e14ad81b8af2.exe)

running 1 test
test cli_happy_path ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.19s

     Running tests\test_py_bindings.rs (target\debug\deps\test_py_bindings-9ef8dc97ededa377.exe)

running 1 test
test python_bindings_smoke ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 3.11s

     Running tests\test_verifier.rs (target\debug\deps\test_verifier-c77db5edd57b8133.exe)

running 3 tests
test verify_file_bad_json ... ok
test verify_file_ok ... ok
test verify_json_ok ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.12s

   Doc-tests poh_ack_rust

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


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
sudo apt-get update
sudo apt-get install python3-dev
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
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_ack$


#　テストはWSL から
cargo test --features python -- --test-threads=1 

error!対処法：
# Ubuntu 22.04 / WSL の例 ― 自分の Python の minor を確認して合わせること
sudo apt update
sudo apt install python3.12-dev python3.12-venv pkg-config   # 例: 3.12 系を使っている場合

# 0) 共有ライブラリを持つシステム Python を明示
export PYO3_PYTHON=/usr/bin/python3.12     # ← ここを固定

■　いま何が起きているか
test_py_bindings.rs 自身が use pyo3::* を行う
→ そのテスト・クレート（＝バイナリ）にも pyo3 が静的リンクされる
Cargo.toml の [dev‑dependencies] では
pyo3 = { version = "0.25", default-features = false,
         features = ["extension-module", "abi3-py312"] }   # ←ここ
と auto‑initialize を付けていないため
PyO3 は「拡張モジュールを作る前提」（埋め込みでなく動的ロード）と判断し、
リンカに ‑lpython3.12 を 渡しません。
その結果、Python のシンボルが一切解決できず大量の
undefined reference to Py*** エラーになります。

修正方法
1. Cargo.toml を 1 行変えるだけ
 [dev-dependencies]
 pyo3 = { version = "0.25", default-features = false,
-         features = ["extension-module", "abi3-py312"] }
+         features = ["extension-module", "abi3-py312", "auto-initialize"] }
auto‑initialize を付けることで
実行ファイル側 に “Python 組み込みモード” のリンクオプションが入り、
‑lpython3.12 が自動で追加されます。
本体ライブラリ側（[features] python = ...) は既に
auto‑initialize が入っているので変更不要です。


入れたあと そのまま再ビルド すれば OK
cargo clean
maturin develop --release 
さらに.dll →　.pydにコピーして (Windows側からもmaturin developしないとtarget\に入らないので注意！)
cargo test --features python -- --test-threads=1