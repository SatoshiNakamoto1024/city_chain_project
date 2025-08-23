rvh_faultset/                                     ← リポジトリルート
├── README.md                                     ← プロジェクト概要・ビルド & テスト手順
├── LICENSE                                       ← Apache-2.0 など
├── rvh_faultset_integration.py                   ← rust・pythonの統合テスト
├── .gitignore                                    ← target/, __pycache__/ など
├── .github/
│   └── workflows/
│       └── ci.yml                                ← cargo test → maturin build → pytest → cargo bench
│
├── rvh_faultset_rust/                            ← Rust コア & Pythonバインディング
│   ├── Cargo.toml
│   ├── pyproject.toml　　　　　　　　　　　　　　  ← Rust側のbist\吐き出し用
│   ├── src/
│   │   ├── lib.rs                                ← `pub mod faultset; pub mod error; pub use faultset::*;`
│   │   ├── faultset.rs                           ← 障害時フォールバックアルゴリズム本体
│   │   ├── error.rs                              ← `#[derive(Error)]` 共通エラー型
│   │   ├── bindings.rs                           ← PyO3 での `#[pymodule]` ラッパー
│   │   ├── main_faultset.rs                      ← CLI サンプル (`--bin main_faultset`)
│   │   └── tests/
│   │       ├── test_faultset.rs                  ← Rust 単体テスト
│   │ 　    └── test_cli.rs    　　　　　　　　　　 ← CLIテスト
│   │ 　    └── test_py_bindings.rs    　　　　　　← pyo3 経由で呼び出し
│   └── benches/
│       ├── bench_faultset_failover.rs            ← failover ベンチマーク
│       └── bench_faultset_parallel.rs            ← 並列ベンチマーク
│
└── rvh_faultset_python/                          ← Pythonサイドラッパー & pure-Python geohash
    ├── __init__.py
    ├── pyproject.toml                            ← Python側のbist\吐き出し用
    ├── README.md                                 ← Python向け使用例・インストール手順
    ├── rvh_faultset/                             ← Pythonパッケージ本体
        ├── __init__.py
        ├── _version.py
        ├── geohash.py                            ← レイテンシ最適化用 geohash 実装（Python-only）
        ├── faultset_builder.py                   ← geohash→faultset 統合パイプライン
        ├── app_faultset.py                       ← CLIサンプル (`python -m rvh_faultset.app_faultset`)
        └── tests/
            └── test_faultset.py         　　　　　　　← pytest テスト

🎯 rvh_trace_rust で出来ること
a:機能
b:何が嬉しい？
c:どこで使う？

a:1-shot 初期化 init_tracing(level)
b:🔧 tracing の Subscriber と OTLP エクスポーターを 一度だけ 構築。Stdout フォーマット＋OpenTelemetry Collector 送信がワンライナー
c: アプリ起動時／テストの #[test] 前

a:Span 生成 new_span(name)
b:Rust から tracing::span!(INFO, …) を安全ラップ
c:ロジックの入口・I/O 境界など

a:スコープ実行 in_span(name, fields, f)
b:let _enter = span.enter(); のボイラープレートを隠蔽し、
キー/値をまとめてレコード
c:小粒な処理を包む時

a:マクロ
b:record_span!("op", user = 42)	1 行で Span 作成＋enter。引数は ?Debug で自動フォーマット
c:ハンドラ関数の先頭など

a:PyO3 バインディング
b:rvh_trace.init_tracing() / rvh_trace.span() が Python から呼べる
c:pytest・Jupyter で Rust 側のトレースを共有

a:CLI デモ cargo run --bin main_trace
b:Rust-only 環境で Collector 送信を試す
c:動作確認・運用スクリプト

a:Tokio-compatible
b:pyo3_asyncio 経由で asyncio⇄Tokio ブリッジを自動生成
c:Python async と Rust async の混在

🛠️ 内部構成ざっくり
src/
├── trace.rs      ← 実装の心臓部
│   ├─ OnceCell で単一初期化
│   ├─ stdout fmt Layer
│   └─ opentelemetry_otlp::new_pipeline()
├── bindings.rs   ← #[pymodule] rvh_trace
│   └─ future_into_py で async context-manager を返す
└── lib.rs        ← 再エクスポート & optional CLI

OTLP 送信先
new_exporter().tonic() はデフォルトで
http://localhost:4317（Collector 標準ポート）へ gRPC 送出します。

変更したい場合は OpenTelemetry 環境変数がそのまま効きます。
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.your-svc.local:4317
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer xxx"

📝 Rust からの使い方
use rvh_trace_rust::{init_tracing, record_span};

fn main() -> anyhow::Result<()> {
    // ① 初期化（何度呼んでも 1 回だけ）
    init_tracing("info")?;

    // ② ざっくり span
    let span = record_span!("startup", node = "edge-42");
    let _e = span.enter();
    tracing::info!("service boot");

    // ③ 処理を in_span で包む
    rvh_trace_rust::in_span(
        "heavy_job",
        &[("items", &1234)],
        || {
            // 重い処理
        },
    );

    Ok(())
}

単体テストで
#[test]
fn it_traces() {
    rvh_trace_rust::init_tracing("debug").unwrap();
    tracing::debug!("hello from test");
}

🐍 Python 側
import asyncio
import rvh_trace  # maturin develop 済み wheel

rvh_trace.init_tracing("debug")   # Rust と同じ stdout ＋ OTLP

async def main():
    async with rvh_trace.span("py_task", user="alice"):
        await asyncio.sleep(0.1)

asyncio.run(main())
span() は async context-manager なので with も async with も対応。

🚀 CLI デモ
cargo run -p rvh_trace_rust --bin main_trace --features cli

# -> INFO  span{name=demo_cli}: hello from CLI
引数を付けたい場合は自前 CLI を bindings::cli_main か
examples/ に生やしてカスタムしてください。

よくある質問
Q	A
ログだけで良い時は？	init_tracing("info") だけで OK。Collector が無くても stderr にフォールバックしませんが、Export エラーは握り潰される設計です。
Collector が止まっているときは？	OTLP レイヤは内部キューに 65 536 span まで保持し、溢れると drop。トレース自体が落ちることはありません。
async-std ランタイムで使える？	OTLP exporterが Tokio runtime を要求するため Tokio 必須 です。Rust 側が async-std の場合は tokio::runtime::Handle::try_current() で包む or blocking fallback を実装してください。

これで「何が出来るか」「どう呼ぶか」「カスタムポイントはどこか」が一通りわかるはずです。
Collector を立てて docker run --name otel-collector -p 4317:4317 otel/opentelemetry-collector:latest で眺めてみると動作が掴みやすいですよ！

# 主なポイントは、
span.record(...) の第一引数 に渡すフィールド名は &str（すでに実装されている AsField）でOKなので、そのまま渡します。
記録する値 は .as_str() で文字列スライスにし、Value トレイトが実装されている型にします。
record_span! マクロ はクレートルートにしか定義しないようにし、重複を取り除きます。
OTLP エクスポーター は opentelemetry_otlp::new_exporter().tonic() を使います。


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


D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust>maturin build --release -o dist
🔗 Found pyo3 bindings with abi3 support for Python ≥ 3.8
📡 Using build options features, bindings from pyproject.toml
   Compiling pyo3-build-config v0.18.3
   Compiling pyo3-ffi v0.18.3
   Compiling pyo3 v0.18.3
   Compiling pyo3-asyncio v0.18.0
   Compiling rvh_trace_rust v0.1.0 (D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust)
warning: unused import: `bindings::*`
  --> src\lib.rs:28:9
   |
28 | pub use bindings::*;
   |         ^^^^^^^^^^^
   |
   = note: `#[warn(unused_imports)]` on by default

warning: unused variable: `py`
  --> src\bindings.rs:11:14
   |
11 | fn rvh_trace(py: Python<'_>, m: &PyModule) -> PyResult<()> {
   |              ^^ help: if this is intentional, prefix it with an underscore: `_py`
   |
   = note: `#[warn(unused_variables)]` on by default

warning: `rvh_trace_rust` (lib) generated 2 warnings (run `cargo fix --lib -p rvh_trace_rust` to apply 1 suggestion)
    Finished `release` profile [optimized] target(s) in 10.98s
⚠️  Warning: Couldn't find the symbol `PyInit_rvh_trace_rust` in the native library. Python will fail to import this module. If you're using pyo3, check that `#[pymodule]` uses `rvh_trace_rust` as module name
📦 Built wheel for abi3 Python ≥ 3.8 to dist\rvh_trace_rust-0.1.0-cp38-abi3-win_amd64.whl


# テスト時の注意
#　Cargo.tomlに必須事項を入れる
# Async runtime
tokio       = { version = "1.37", features = ["rt-multi-thread", "macros", "time"] }

# PyO3 bindings
pyo3                  = { version = "0.18", features = ["extension-module","abi3-py38"] }
pyo3-asyncio = { version = "0.18", features = ["attributes", "tokio-runtime", "testing"] }

・Tokio
rt-multi-thread - ランタイム本体
macros - #[tokio::test] などを使うために必要

・pyo3-asyncio
tokio-runtime - Tokio 連携
testing - #[pyo3_asyncio::tokio::test] マクロ用

の両方が入っているので十分です。

#　テスト準備
なぜ必要なのか
pyo3-build-config::add_extension_module_to_path! マクロは 0.21 系に移動した、または非推奨になっており、0.18 系には存在しません。

そこで手動でビルド済みの .so/.dylib/.dll を探し
Windows なら .dll→.pyd にコピー
そのディレクトリを PYTHONPATH に追加
といった処理を行うことで、テスト実行時に Python が拡張モジュールを正しく読み込めるようにします。
これで cargo test → Rust 側全テスト、さらに Python バインディングのテストまで一気通貫でパスするはずです。

・まずは.dll は下記にある
D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\target\debug\deps\rvh_trace_rust.dll

・つぎに、.pyd をコピーする
D:\city_chain_project\.venv312\Lib\site-packages\rvh_trace_rust\rvh_trace_rust.cp312-win_amd64.pyd
ここにあるわ。

・テストコードを修正するポイントまとめ
find_cdylib() …target/{debug,release}/deps/ 以下を再帰検索して拡張モジュールファイル（.dll / .so / .dylib）を見つけます。
ensure_pyd() …Windows では .dll を .pyd にコピー。Linux/macOS はそのまま使います。
add_pythonpath() …拡張モジュールのあるディレクトリを PYTHONPATH に追加し、テスト中の Python インタープリタがモジュールを見つけられるようにします。
以降は py.import("rvh_faultset_rust") で正常にロードできるはずです。

・ Maturin で先にインストールしてしまう
開発マシン・CI 共に少し手順を増やしてよいなら、テストの前に maturin develop --release（または pip install .）で拡張モジュールを仮想環境にインストールしてしまうのが簡単です。
そうすれば、cargo build → cargo test ではなく、次のように流せば OK:
cd rvh_trace_rust
maturin develop --release
cd ../rvh_trace_python
pip install .   # or pip install -e .
cd ../
cargo test      # Python の mv はもう不要
CI の .github/workflows/ci.yml にも、この手順を足してください。

# lib.rsへの追加
mod bindings;          // ← #[pymodule] を含む
pub use bindings::*;   // Python ラッパーを re-export

これを入れておけば、cargo test（あるいは CI 上での cargo test）だけで、Rust のユニットテスト・CLI テスト・Python バインディングテストまで一貫して動作確認できるようになります。

src/lib.rs に mod bindings; pub use bindings::*; を必ず追加
cargo build または maturin develop --release → 上記のテストを再実行

これで .pyd／.so に正しい PyInit_rvh_trace_rust シンボルが含まれ、Python 側からも問題なく import rvh_trace_rust に成功するはずです。

# Cargo.tomlの対応
→　pyo3-asyncio (for Python ≥3.8 / Python 3.12 対応)　では動かない！
　 pyo3-async-runtimes　version = "0.25"　でないと動かないので、ここに統一する！！
　他のモジュールもここに統一する！
pyo3 = { version = "0.25", features = ["extension-module"] }
pyo3-async-runtimes = { version = "0.25", features = ["tokio-runtime"] }


#　lib.rs のtokio対応の修正方針
doctest が自動実行されても ランタイムを確保するか
そもそも 実行させずコンパイルだけに留める
今回は 実行不要のガイドコード なので、最小変更で no_run フラグを付けて
「コンパイル確認のみ・実行しない」形にします。

本番実装用・修正版 src/lib.rs（全文）
//! rvh_trace_rust: Rust core for tracing & metrics
//!
//! ## Rust Usage <!-- doctest -->
//! ```no_run
//! // `no_run` を付けて doctest 実行を抑止 (コンパイル確認のみ)
//! rvh_trace_rust::init_tracing("info").unwrap();
//! let span = rvh_trace_rust::new_span("example");
//! let _enter = span.enter();
//! tracing::info!("inside span");
//! ```
//!
//! ## Python Usage (after `maturin develop`)
//! ```python
//! import rvh_trace
//! rvh_trace.init_tracing("info")
//! with rvh_trace.span("py_example", user=42):
//!     pass
//! ```

// ──────────────────────────────────────
// パブリック API
// ──────────────────────────────────────
pub mod trace;
pub mod error;

pub use trace::{init_tracing, new_span, in_span};
pub use error::TraceError;

// ──────────────────────────────────────
// PyO3 バインディングの再公開
// ──────────────────────────────────────
mod bindings;
pub use bindings::*;
#[cfg(feature = "cli")]
pub use bindings::cli_main;

// ──────────────────────────────────────
// （内部）PyO3 用スパンガード型
// ──────────────────────────────────────
use pyo3::{pyclass, pyfunction, pymethods, types::PyAny, PyResult};
use tracing::Level;

#[pyfunction]
fn span(name: &str) -> PyResult<PySpanGuard> {
    let _span = tracing::span!(Level::INFO, "span", name = name);
    let _enter = _span.enter();
    Ok(PySpanGuard {})
}

#[pyclass]
pub struct PySpanGuard;

#[pymethods]
impl PySpanGuard {
    fn __enter__(&self) {}
    fn __exit__(&self, _ty: &PyAny, _val: &PyAny, _tb: &PyAny) {}
}

ポイント
修正	意味
no_run	doctest が「コンパイル のみ」になり、Tokio ランタイム不要で失敗しなくなる
コメントに <!-- doctest --> を残す	後で見ても ここが doctest と分かりやすい


# test_py_bindings.rs でパニックを起こす対策
なぜ他のテストは通るのか
test_cli / Rust-only テスト は #[tokio::main] や #[tokio::test] で 最初から Runtime 内 になり、問題なし。
Python 経由 では import 時にまだ Runtime が無い → tonic が spawn できず panic。これが唯一の差です。

Python から rvh_trace_rust.init_tracing() を呼ぶ経路だけ
tokio の「現在のランタイム」が無いまま OpenTelemetry-OTLP 初期化が走り、
内部で発火する tokio::spawn() が “there is no reactor running” パニックを起こしています。

何が起きているか
ステップ	詳細
① Python 側で import rvh_trace_rust → init_tracing("debug") を呼ぶ	この時点では Tokio ランタイムが存在しない
② init_tracing 内で Runtime::new() を生成して OnceCell に保持	しかし そのランタイムを「現在の」ランタイムとして enter していない
③ opentelemetry_otlp::new_pipeline().install_simple() が呼ばれる	OTLP exporter は gRPC(Tonic) のバックグラウンドタスクを tokio::spawn() で起動する
④ tokio::spawn() が Handle::current() を取ろうとする	ハンドルが無いため panic: “there is no reactor running” が発生
github.com
docs.rs
users.rust-lang.org

同様の報告は OpenTelemetry/Tonic や tokio-postgres でも多数あり、
「ランタイムを生成したら rt.enter() で 現在の ランタイムにしてから非同期初期化を行う」
のが定石とされています
github.com
tokio.rs
stackoverflow.com

修正ポイント
1. init_tracing を “enter 付き” に書き換える
pub fn init_tracing(filter: &str) -> Result<(), TraceError> {
    SUB_INIT.get_or_try_init(|| {
        // すでにランタイム下ならそのまま
        if Handle::try_current().is_ok() {
            return setup_subscriber(filter);
        }

        // なければ builder で作成し OnceCell に保持
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .map_err(|e| TraceError::Init(e.to_string()))?;

        // ★ ここがポイント ── “現在のランタイム” として enter
        let _guard = rt.enter();           // EnterGuard keeps this thread inside rt
        let res    = setup_subscriber(filter);   // ここで install_simple が spawn しても OK
        RUNTIME.set(rt).ok();              // drop させず保持
        res
    })?;
    Ok(())
}

Runtime::enter() により このスレッドがランタイムの Reactor/Timer を持つ 状態になるため、
install_simple() 内の tokio::spawn() が安全に動ける
docs.rs
scs.pages.ub.uni-bielefeld.de

Guard が drop された後も、Runtime は OnceCell に格納してあるので
OTLP exporter のバックグラウンドタスクが生き続ける。

2. 依存 crate 側の “別案” にしない理由
opentelemetry-otlp には blocking 版 (install_batch) や
tokio::spawn を使わない exporter は現状無い
docs.rs

pyo3_async_runtimes の future_into_py は「すでに動いているランタイム」を前提に
spawn_local で Future を駆動する設計で、本件の panic とは別レイヤ
traffloat.github.io

確認手順
上記パッチを適用して cargo test --tests を再実行

test_py_bindings が PASS する

Python 単体でも OK
python - <<'PY'
import rvh_trace_rust, asyncio
rvh_trace_rust.init_tracing("debug")
asyncio.run(rvh_trace_rust.span("py_demo"))
PY
ログが流れ、クラッシュしないことを確認。

#　参考になった資料
Tokio “no reactor running” パニックの原因と対策
github.com

Tonic / OpenTelemetry で同様の症状が出る issue 列
docs.rs
github.com

Runtime::enter() の公式ドキュメントと例
docs.rs
reddit.com

OpenTelemetry-OTLP install_simple が内部で tokio::spawn を使う実装部
docs.rs

pyo3_async_runtimes::tokio::future_into_py の動作説明
traffloat.github.io

StackOverflow の類似質問 (tokio-postgres 等)
stackoverflow.com
stackoverflow.com
stackoverflow.com

これで Python でも Rust でも同じ初期化関数を使い回しつつ、
Tokio ランタイムが必ず存在する状態で OTLP exporter を立ち上げられる ようになります。

# いま起きている IndentationError の原因
py.run() に渡す Python スクリプト文字列の 1 行目と 2 行目が
どちらも 8 スペースで字下げされているためです。

Python では
import asyncio          # 行頭にインデント不可
async def _main():      # ← ここも行頭
    await trace.span()  # ← 本体は 4 つ以上インデント
というレイアウトでないと「関数定義の次にインデントされた
ブロックが無い」と判定されます。
トップレベルでインデントが始まっている ( import …)
→ パーサがエラーを出します。

修正ポイント（重要！）
// ② coroutine を定義（← 左端に寄せる！）
let code = CString::new(
    //      ↓ 行頭に一切インデントを入れない！
    "async def _main():\n    await trace.span('rust_test')\n"
).unwrap();

/* ────────────────────── 省略 ────────────────────── */

// ③ _main() を eval して Future を得る
let fut = py.eval(
    // ここも CString を都度生成（&CStr が欲しいだけ）
    CString::new("_main()").unwrap().as_c_str(),
    Some(&locals),　//　←　ここを２つ並ぶのが違和感あるがこれで正解！
    Some(&locals),
)?;

変更点まとめ
行	before	after
①	"import asyncio\n\ async def ..."	"import asyncio\n\\nasync def ..."
※ 行頭の空白を削除
②	await trace.span('rust_test') (そのまま)	先頭 4 スペースを入れる
③	文字列リテラル " _main() " をそのまま渡していた	CString::new("_main()").unwrap().as_c_str() に置換

補足
1 行目の末尾に \n\ と書くと 行頭にインデントが残りやすい ので、
上のように 行頭ゼロ から始めるのが安全です。


✅ まとめ
問題点	解決策
target/debug に .pyd がない	正常です、.pyd は仮想環境の site-packages に入ります
Rustのテストで .pyd を探している	find_shared_lib() は不要、Pythonから直接 import を試すコードに変える
.whl ができてるけど .pyd が見えない	pip install すれば .pyd が見えるようになります

1 ️⃣　RUST_BACKTRACE=1 で panic のフルスタックを出す
やること	手順	見えるもの
バックトレースを有効化	powershell<br>set RUST_BACKTRACE=1<br>cargo test --test test_py_bindings -- --nocapture<br>	panic 行を含む 完全なスタックトレース がコンソールに流れます。--nocapture を付けると eprintln! などの出力も隠れません

ポイント
“どの crate / ソース行でパニックが起きたか” が一目で分かる
テストを絞る (--test) とログが短くて読みやすい

2 ️⃣　tracing::debug! + RUST_LOG でランタイム検出の流れをログ出力
やること	手順	見えるもの
コード側に debug ログを挿す	rust<br>// trace.rs (init_tracing の最初あたり)<br>tracing::debug!("Handle::try_current() = {:?}", tokio::runtime::Handle::try_current());<br>
環境変数でログレベル指定	powershell<br>set RUST_LOG=rvh_trace_rust=debug,tokio=debug<br>cargo test --test test_py_bindings -- --nocapture<br>	- rvh_trace_rust 自分のログ
- tokio の内部ログ（runtime 生成や spawn など）

ポイント
EnvFilter に RUST_LOG が優先されるので、コード側の EnvFilter::new("info") でも上書き可
ログは色付きで時系列に並ぶので Runtime がいつ出来たか追跡しやすい

3 ️⃣　dbg!() や eprintln!() で即時ダンプ
やること	手順	見えるもの
Rust ↔︎ Python 境界の値を確認	rust<br>// bindings.rs<br>dbg!("before init_tracing");<br>dbg!(Handle::try_current());<br>
テスト実行（--nocapture）	powershell<br>cargo test --test test_py_bindings -- --nocapture<br>	その場所が確実に通ったか・値はどうかを 行番号付きでそのまま表示

ポイント
dbg!() は値とファイル:行番号を自動で付けてくれるので場所特定が速い
panic 前後で 2 箇所入れて「どこまで到達したか」を挟み撃ちで確認できる

4 ️⃣　tokio-console / console_subscriber でタスクを可視化（GUI）
Cargo.toml
[dependencies]
console-subscriber = { version = "0.2", features = ["tokio_unstable"] }
tokio = { version = "1.37", features = ["rt-multi-thread", "macros", "time", "tokio_unstable"] }

main / tests の最初で
console_subscriber::init();   // tracing_subscriber と併用可

別ターミナルで
tokio-console

テスト実行
GUI に spawn / poll / waker 情報がリアルタイム表示され、
panic 直前に どのタスクが動いた／止まった かが分かります。

ポイント：tokio_unstable feature を tokio に付け忘れるとビルドエラーになるので注意。

5 ️⃣　pyo3_async_runtimes::tokio::init の戻り値を確認
やること	手順	見えるもの
初期化結果を dbg!	rust<br>// bindings.rs (pymodule 冒頭)<br>let already = pyo3_async_runtimes::tokio::init( <br> tokio::runtime::Builder::new_multi_thread().enable_all()<br>);<br>dbg!(already); // true なら既に初期化済み<br>
テスト実行	powershell<br>cargo test --test test_py_bindings -- --nocapture<br>	dbg!(already) が true/false どちらか吐くので Runtime 重複判定がすぐ分かる

6 ️⃣　最小 Python スクリプトで import → panic を追跡
ビルドして .pyd / .so を用意
maturin develop --release   # または cargo build && copy → .pyd
VS Code で debug_py.py を作成
import rvh_trace_rust, asyncio, logging
logging.basicConfig(level=logging.DEBUG)
rvh_trace_rust.init_tracing("debug")
asyncio.run(rvh_trace_rust.span("py").__await__())
python -X dev debug_py.py で実行 or デバッガでブレーク

-X dev モードは unawaited coroutine 警告やリソース警告を強制表示

VS Code のデバッガなら Rust パニックと Python スタックを同時に確認可能

うまく行かないときのチェックポイント
チェック	OK の状態
Handle::try_current() before init_tracing()	Err(NoContext) なら自前 Runtime が要る
dbg!(already)	false → true で 2 回目以降は初期化スキップ
RUST_LOG 出力	rvh_trace_rust::trace の debug ログが見える
tokio-console	Reactor が “OFFLINE” になっていない

これらを ひとつずつオン／オフ しながら実行すれば、
「どこで Runtime が無いまま tonic が動こうとしているか」が必ず分かります。
まずは 1️⃣ と 3️⃣ で panic 行直前の値 を確認 → 2️⃣ で流れを追い → 5️⃣ で Runtime 重複有無を確認、
最後に GUI が欲しければ 4️⃣ を付ける、という順で試すのがオススメです。


running 1 test
test test_cli_runs ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.55s

     Running tests\test_py_bindings.rs (target\debug\deps\test_py_bindings-10742091b37017d6.exe)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running tests\test_trace.rs (target\debug\deps\test_trace-2838684b4965306d.exe)

running 1 test
2025-07-03T20:56:49.697885Z  INFO span{name=unit_test}: inside sync span
2025-07-03T20:56:49.699053Z DEBUG buffer closing; waking pending tasks
test test_trace_sync ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s

   Doc-tests rvh_trace_rust

running 1 test
test src\lib.rs - (line 6) - compile ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.11s


# ベンチ (結果は target/criterion/)
まずは、tokioに対応するよう、Cargo.tomlを変更。
criterion = { version = "0.5", features = ["html_reports", "async_tokio"] }

そして、
cargo bench -p rvh_trace_rust

結果は、
   Finished `bench` profile [optimized] target(s) in 2m 08s
     Running unittests src\lib.rs (target\release\deps\rvh_trace_rust-e51c6201cecbd33b.exe)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running unittests src\main_trace.rs (target\release\deps\main_trace-e5cb44290948b232.exe)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

     Running benches\bench_trace.rs (target\release\deps\bench_trace-5ed830b765359369.exe)
Gnuplot not found, using plotters backend
[rvh] init_tracing: Handle::try_current() = Ok(Handle { inner: MultiThread(multi_thread::Handle { ... }) })
new_span_async          time:   [2.7140 ns 2.7742 ns 2.8509 ns]
Found 9 outliers among 100 measurements (9.00%)
  4 (4.00%) high mild
  5 (5.00%) high severe
