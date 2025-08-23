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

1. Rust Core
モジュール	機能	ポイント
ackset.rs	Ack 構造体（id, timestamp, signature, pubkey）と
AckSet（重複検出 & TTL 検証付きコレクション）	すべて no_std 互換。署名には ed25519‑dalek v2 を使用
ttl.rs	validate_ttl(ts, ttl_sec) ― RFC3339 時刻と TTL の比較	単体でも再利用できるユーティリティ
error.rs	一貫した AckError 枚挙型＋thiserror	JSON／Base58／IO／重複などを網羅
main_ack.rs	CLI ツール main_ack --input foo.json --ttl 300	tokio runtime で async with ! だが処理自体は同期
+-------------+     verify()      +-------------+
|  Ack (one)  |  ───────────────▶ |  AckError   |
+-------------+                  +-------------+

2. Python バインディング（PyO3 0.25, ABI3‑py312）
#[pymodule]
fn poh_ack_rust(py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    pyo3::prepare_freethreaded_python();   // GIL 初期化
    bindings::init(py, m)                  // PyAck, PyAckSet, check_ttl
}

PyAck : 1 件をラップ。verify() / verify_async()
PyAckSet : Rust の AckSet をそのまま公開
check_ttl() : TTL だけ欲しい時用
これを maturin build すると
poh_ack_rust‑0.1.0‑cp312‑abi3‑<plat>.whl が生成される。

3. Python ラッパ (poh_ack)
ファイル	主な内容
models.py	AckRequest (pydantic) – 型安全に JSON <-> オブジェクト
verifier.py	verify_ack() / verify_ack_async()
  ↳ PyO3 の Ack を生成して Rust 側で検証
cli.py	poh_ack.cli verify … verify-async …
--json-output を付けると純 JSON を返す

4. テスト & インテグレーション
Rust 側：cargo test
tests/test_cli.rs… 実バイナリ呼び出し
tests/test_py_bindings.rs… PyO3 cdylib smoke‑test
Python 側：pytest、または 統合 poh_ack_integration.py
Rust CLI → OK
Python sync / async API → OK
Python CLI (sync / async) → JSON 出力を検証

　✅ ポイント：Rust モジュールが println! してしまう副作用を
　　integration.py で「最後の JSON 行だけ読む」実装にして吸収。

5. ビルド & 配布フロー
# Rust バイナリ
cargo build --release                       # target/release/main_ack

# Python wheel (ABI3, one‐shot)
maturin build --release                     # dist/poh_ack_rust-*.whl
pip install dist/poh_ack_rust-*.whl

# Editable dev install
maturin develop --release                   # pip install -e .

# Python ラッパは普通に
pip install -e poh_ack_python/
Cargo features

デフォルトで py-ext を含むので cargo build だけで PyO3 付き。
build.rs は空 – 静的リンクなど特別なことはしない。

6. 典型的な利用シナリオ
from poh_ack import models, verifier

req = models.AckRequest.parse_file("ack.json")
result = verifier.verify_ack(req, ttl_seconds=300)
if result.valid:
    print("👍 verified!")
else:
    print("❌", result.error)

CLI 派なら:
poh_ack verify --input ack.json --ttl 300 --json-output
→ {"id":"...","valid":true,"error":null}

まとめ
Rust で「正当性検証」「TTL 判定」「重複チェック」まで完結。
PyO3 で Python から同じロジックを呼び出せる（sync/async）。
Python ラッパ でスキーマ・CLI・高レベル API を提供。
統合テスト が Rust↔Python 間のずれを常に検出。
ABI3 wheel を配布すれば Python 3.12 以降どこでも動く。

これで PoH‑ACK スタック全体の構成とデータフローがクリアになるはずです 🚀



各クレート（poh_storage/、poh_ttl/、poh_network/）それぞれで editable インストール：
# そして poh_ack
cd ../poh_ack_python
pip install -e '.[test]'
#　wheel を dist\ に置きたいなら comandプロンプトから（ややこしいね。。）
pip install -e .

python -m pip install --upgrade build   # 必須
python -m pip install --upgrade twine  # PyPI に上げるなら
python -m build             # ← wheel と sdist の両方を生成

cd ../poh_ack_rust
maturin build --release -o ../poh_ack_python/dist　をする。


# スクリプトに実行ビットを付けるか、Python で起動
chmod +x poh_ack_integration.py          # ← 一度だけ

python poh_ack_integration.py

# test errorが止まらない。どうする？
もう一度整理してみましょう。Windows で起きているのは、
Fatal Python error: PyInterpreterState_Get: the function must be called with the GIL held …

という、Rust/PyO3 拡張モジュール poh_ack_rust の初期化時に GIL（Global Interpreter Lock）が正しく取得できずクラッシュしてしまう、という問題です。Linux (WSL) 側では大丈夫なのに、Windows だけ落ちるのは、ビルド時に「Pythonランタイムの自動初期化／GIL準備」のフラグが有効になっていないためです。

以下の２点を必ず両方とも行なってください。
1. Cargo.toml の依存に auto-initialize を追加
--- poh_ack_rust/Cargo.toml
+++ poh_ack_rust/Cargo.toml
@@ [dependencies]
- pyo3 = { version = "0.25", features = ["abi3-py312", "extension-module"] }
+ pyo3 = { version = "0.25", features = ["abi3-py312", "extension-module", "auto-initialize"] }
これで、拡張モジュールがロードされたタイミングで内部的に Py_Initialize() 相当の呼び出しと GIL の初期化が行われるようになります。

2. pyproject.toml の tool.maturin にも同じフラグを追加
--- poh_ack_rust/pyproject.toml
+++ poh_ack_rust/pyproject.toml
@@ [tool.maturin]
-features = ["python"]
+features = ["python", "auto-initialize"]
 bindings = "pyo3"
 cargo-extra-args = ["--locked"]
 platform-tag = "manylinux2014_x86_64"
maturin がデフォルトで有効にする feature を「python」だけでなく「auto-initialize」まで含めるようにします。


maturin develop --release --features python
をしてから、
(linux-dev) satoshi@LAPTOP-88SH779D:/mnt/d/city_chain_project/DAGs/libs/algorithm/poh_ack$ python poh_ack_integration.py
✅ Rust CLI passed
✅ Python sync API passed
✅ Python async API passed
✅ Python CLI sync passed
STDOUT→ {"id":"py_cli_sync_integration","valid":true,"error":null}

STDERR→ <frozen runpy>:128: RuntimeWarning: 'poh_ack.cli' found in sys.modules after import of package 'poh_ack', but prior to execution of 'poh_ack.cli'; this may result in unpredictable behaviour

✅ Python CLI async passed

 All Rust & Python integration tests passed!


# 使い分け
Python 拡張（feature = "python"）を有効にしたときに、テストバイナリにも Python のシンボルをリンクさせる必要があります。今のままだと cargo test --features python で tests/test_py_bindings.rs がビルドされますが、リンク時に PyObject_Vectorcall や _Py_DecRef といった C‐API シンボルが見つからずエラーになっています。

最小修正手順
Cargo.toml に build-dependencies セクションを追加
pyo3-build-config をビルドスクリプト向けに入れます（現状は dev-dependencies のみなので動きません）。
[package]
name         = "poh_ack_rust"
version      = "0.1.0"
edition      = "2021"
# …省略…

[build-dependencies]
pyo3-build-config = "0.25"

[dev-dependencies]
#--- 以下の行は残しておいてもかまいませんが、build-dependencies側で十分です
# pyo3-build-config = "0.25.0"

build.rs を修正
feature = "python" が有効なときに、Python ライブラリへのリンク引数を追加する呼び出しを入れます。プロジェクト直下の poh_ack_rust/build.rs を以下のようにしてください。
// poh_ack_rust/build.rs
fn main() {
    // Python バインディング用に libpython をリンク
    #[cfg(feature = "python")]
    pyo3_build_config::add_extension_module_link_args();
}

もしまだ build.rs がなければ、プロジェクトルートに作成してください。

[features]
# wheel ビルドや Python から import するとき
python-ext = ["pyo3/extension-module"]
# Rust 側で直接実行・テストしたいとき
python-embed = ["pyo3/auto-initialize", "pyo3/abi3-py312"]  # abi3 は任意
default = []          # デフォルトはどちらもオフに

これで…
# 通常のユニットテスト（Rust コアのみ）
cargo test

# Pythonバインディングを含めたテスト
wheel を作るとき
maturin build --release --features python-ext

Rust のユニットテストを回すとき
cargo test --features python-embed

…が両方通るようになります。概念０–３に沿って、Python 機能は feature = "python" で切り分け、必要最小限のビルドスクリプト変更だけでリンクエラーを解消しています。


# 補足
以下の手順で進めれば、pip install -e . を使わず、かつ「Rust‐only ↔ Python 拡張込み ↔ wheel 出力」の３モードをきちんと切り替えられます。

▶ Rust 側
Rust‐only のユニットテスト
PyO3 をリンクしない高速チェックです。
cargo test --workspace --no-default-features

Python バインディングを含めた Smoke & 統合テスト
feature = "python"（別名 py-ext）を有効にして、PyO3 ↔ Python のスモークテストも走らせます。
cargo test --workspace --features python

※Cargo.toml で default = ["core","py-ext"] にしていれば、このステップは --features python を省略しても OK です。


ネイティブバイナリと Python 拡張をビルド＆インストール
まずは optimized ビルド（バイナリだけ）。
cargo build --release

次に maturin で Python 拡張をカレント venv にインストール。
maturin develop --release
（--features python は maturin が自動で付与します）

wheel／sdist を出力
配布用パッケージを dist/ に作ります。
maturin build --release -o dist/

▶ Python 側
ワークスペース共通 venv を有効化
例：python -m venv .venv && source .venv/bin/activate

Rust 拡張込みのパッケージをインストール
pip install -e . は禁止なので、maturin で開発インストールします。
cd poh_ack_python
2️⃣ 最小の一手で動かす
ステップ A: まず動かすだけ
# venv はもう有効化済みとして
A. もっとも無難な修正
poh_ack_rust/pyproject.toml を開いて
[tool.maturin] に features = ["python"] を追加します。
[tool.maturin]
bindings         = "pyo3"
features         = ["python"]     # ← これを追加
cargo-extra-args = ["--locked"]

cd poh_ack_python
maturin develop --release -m ../poh_ack_rust/Cargo.toml

-m で Rust クレート側の Cargo.toml を指す
wheel がビルド→インストールされる
python -c "import poh_ack_rust; print(poh_ack_rust.__doc__)" が通ることを確認

ポイント
pytest からは Python パッケージ側の __init__.py が呼ばれるだけで良い
Rust のテスト (cargo test) と分けて考える


テストを実行
Python 側ユニット＆統合テストを走らせます。
pytest -v poh_ack/tests

（必要なら）wheel を手動で作ってインストール
pip install dist/*.whl → 同じく pytest で動作確認できます。
maturin build --release -o dist/
pip install dist/poh_ack-*.whl
pytest -v poh_ack/tests

ポイントまとめ
--features python
Rust の cargo コマンドで「PyO3 を含める」モードに切り替えたいときだけ指定。単体ロジックのテストは --no-default-features、バインディング検証は --features python で。

py-ext
Cargo.toml のエイリアス名です。--features py-ext と指定しても同じ働きをします。

pip install -e . 禁止
Python 側は必ず maturin develop（または wheel → pip install dist/*.whl）でパッケージを取り込みます。

これで Rust↔Python↔wheel のビルド＆テストフローが明確になります。


# workspaceからテストする
Rust サブクレート poh_ack_rust/Cargo.toml を
「ワークスペース依存に乗せ替える」最小パッチ
 [package]
 name         = "poh_ack_rust"
@@
 repository   = "https://github.com/your_org/poh_ack"

-[features]
-# core = Rust だけ使う場合の最小機能 (bin/main_ack 用)
-core    = []
-# python = PyO3 バインディングを含む完全版
-python  = ["pyo3/extension-module", "pyo3/abi3-py312", "pyo3/auto-initialize"]
-# デフォルトはどちらもオフに
-default = []
-# wheel ビルドや Python から import するとき
-python-ext = ["pyo3/extension-module"]
-# Rust 側で直接実行・テストしたいとき
-python-embed = ["pyo3/auto-initialize", "pyo3/abi3-py312"]  # abi3 は任意
+[features]
+# ──────────────────────────────────────────────
+core          = []                 # CLI だけ使うとき
+python        = ["pyo3/extension-module",
+                 "pyo3/abi3-py312",
+                 "pyo3/auto-initialize"]  # maturin / pytest 用
+python-ext    = ["python"]         # Wheel-build（maturin build）
+python-embed  = ["python"]         # cargo test --features python-embed
+default       = []                 # 明示しないとどちらも off
diff
Copy
Edit
 [lib]
 name       = "poh_ack_rust"
 crate-type = ["cdylib", "rlib"]
 path       = "src/lib.rs"
@@
 [dependencies]
-bs58          = "0.4"
-ed25519-dalek = { version = "2", default-features = false, features = ["pkcs8", "rand_core"] }
-tokio         = { version = "1.37", features = ["rt","rt-multi-thread","macros","time"] }
-once_cell     = "1.19"
+# ────── 共通ライブラリは workspace = true でバージョンを一元化 ──────
+bs58                 = "0.4"                            # ルートに無いので直書き
+ed25519-dalek        = { version = "2",
+                         default-features = false,
+                         features = ["pkcs8", "rand_core"] }
+tokio                = { workspace = true,
+                         features = ["rt","rt-multi-thread","macros","time"] }
+once_cell            = "1.19"

 # --- errors & CLI etc. ----------------------------------------------------
-chrono        = { version = "0.4", features = ["serde"] }
-serde         = { version = "1.0", features = ["derive"] }
-serde_json    = "1.0"
-thiserror     = "1.0"
-anyhow        = "1.0"
+chrono               = { version = "0.4", features = ["serde"] }  # ルートに無い
+serde                = { workspace = true, features = ["derive"] }
+serde_json           = "1.0"
+thiserror            = { workspace = true }
+anyhow               = { workspace = true }
 clap                 = { version = "4.5", features = ["derive"] }
 indoc                = "1"

 # --- PyO3 & asyncio bridge -----------------------------------------------
-pyo3          = { version = "0.25",
-                  features = ["abi3-py312", "extension-module", "auto-initialize"] }
-pyo3-async-runtimes = { version = "0.25", features = ["tokio-runtime"] }
+pyo3                 = { workspace = true,
+                         features = ["abi3-py312","extension-module","auto-initialize"] }
+pyo3-async-runtimes  = { workspace = true, features = ["tokio-runtime"] }
diff
Copy
Edit
 [dev-dependencies]
@@
-# テスト用に再度 pyo3 を宣言していたが、workspace で十分
-pyo3            = { version = "0.25", default-features = false,
-                    features = ["extension-module", "abi3-py312", "auto-initialize"] }
+pyo3                 = { workspace = true,
+                         default-features = false,
+                         features = ["extension-module","abi3-py312","auto-initialize"] }
 pyo3-build-config    = "0.25.0"
なぜこれで良いの？
ポイント	理由
workspace = true を使う	ルート [workspace.dependencies] で版本号を一元管理 → “上げ忘れ”による依存競合を防止
feature ツリーを整理	python を親にして python-ext / python-embed はそれを再利用 → フラグ爆発を回避
pyo3 を 1 か所に	バージョン & feature が完全一致しないとビルドが分割されてしまうため


あと、cargo.tomlに下記を追加
2. Cargo.toml に build-script を登録
[package]
build = "build.rs"

[[test]]
name = "test_py_bindings"
path = "tests/test_py_bindings.rs"
required-features = ["python"]


これで動かす手順（再確認）
# Rust (core only)
cargo test --workspace

# Rust + Python テスト
cargo test -p poh_ack_rust --features python

# Python 側
cd DAGs/libs/algorithm/poh_ack/poh_ack_python
maturin develop --release -m ../poh_ack_rust/Cargo.toml
pytest -v poh_ack/tests
この構成なら ルートの Cargo.toml を変更せず ワークスペース全体で
Rust / Python のテストを安定して回せます ✅

# 修正パターン B — ワークスペース全体の target-dir を固定
ワークスペース直下に .cargo/config.toml を置きます。
# D:\city_chain_project\.cargo\config.toml
[build]
target-dir = "target-release"   # <- debug 用と分離

[profile.release]
# LTO は prefer-dynamic と相性が悪いので off
# lto = "thin"   <- コメントアウト
codegen-units = 1
opt-level     = "z"


注意: 既存の CI やローカルスクリプトに CARGO_TARGET_DIR を
上書きしている箇所があればそちらが優先されます。

B. target-dir 固定	全クレートでビルド成果物が一箇所に集まる
（キャッシュ効率◎）	既存スクリプトで --target-dir を弄っていると衝突


3. wheel ビルド & Python テストを別プロセスで
:: 1) Rust embed DLL を release でテスト
cargo test -p poh_ack_rust --release --features python-embed -- --test-threads=1

:: 2) wheel / pyd を別 target フォルダでビルド
set CARGO_TARGET_DIR=target-ext
maturin develop --release -m DAGs\libs\algorithm\poh_ack\poh_ack_rust\Cargo.toml

:: 3) Python ユニットテスト
pytest -v poh_ack\tests


# 何が二重になるのか？
| ライブラリ                 | Linux (.so)     | Windows (.dll / .pyd)            |
| ------------------------- | ------------    |    ----------------------------- |
| **`pythonXY`** 本体       | 1 個にまとまる   | venv の pythonXY.dll と Rust が静的リンクした pythonXY.lib の *二重存在* が起きる |
| **Rust 標準ライブラリ** (`std-*.dll`) | 1 個  | `debug\std-*.dll` と `release\std-*.dll` が同時に入ることがある            |
| **OpenSSL / bcrypt** 等   | distro 共有 SO  | vcpkg / system32 / Cryptography wheel が全部別 DLL                 |

→ どれかが 異なる CRT / vtable を持っている状態で相互呼び出しすると 100% AV になります。

再現する手順になっている理由
cargo test --profile=debug --features python-embed
→ target\debug\poh_ack_rust.dll + std-*.dll(debug) が生成

maturin develop --release
→ target\release\poh_ack_rust.pyd + std-*.dll(release) が生成

pytest が import poh_ack_rust した瞬間
Python は release 版 .pyd をロード

その中に std-*.dll(debug) 参照が残っている（link-time の依存）
直後 cryptography など C 拡張が 別バージョンの CRT を要求 → 競合 → AV
Linux では DT_NEEDED に同じ libstd-xxxx.so が走ればうまくシンボル解決されるので落ちません。

解決パターン 3 択
| 方法                       | 長所                            | 短所                    |
| ----------------------     | ---------------------------- - | ----------------------- |
| ① すべて Release だけで統一 | 一番シンプル。CI も早い          | debug でデバッグしたい時に不便      |
| ② すべて Debug だけで統一　 | `cargo test` ↔ `pytest` 往復が速い| wheel サイズが大きくなる、配布には不向き |
| ③ 同じ target-dir に “dual profile” を置かない**<br>（`target-debug` と `target-release` を分ける） | ビルドモードを切り替えても競合しない        | 毎回フル再ビルドが必要で時間がかかる      |


# 実践手順（おすすめ：① Release に統一）
Rust 側すべて Release でビルド
cargo clean -p poh_ack_rust
cargo test   --release -p poh_ack_rust --features python-embed

Python 拡張も同じ artefact を使う
set CARGO_TARGET_DIR=target-release
maturin develop --release `
       -m DAGs\libs\algorithm\poh_ack\poh_ack_rust\Cargo.toml `
       --features python-ext   # ★ extension-module だけ

pytest
pytest -q poh_ack/tests

ポイントは “同じ target ディレクトリ ＋ 同じビルドプロファイル” で
poh_ack_rust.{pyd,dll} と std-*.dll が 1 ペアしか存在しない状態にすることです。

まだ落ちる場合のチェックリスト
| チェック項目                              | 確認方法                        |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `where std-*.dll` が 2 か所に無いか       | `where /R %CD% std-*.dll`       |
| `poh_ack_rust.*` が複数コピーされていないか  | `dir /S /B poh_ack_rust.*`    |
| Python が 32bit / Rust が 64bit で食い違っていないか   | `python -c "import struct,platform,sys;print(platform.architecture(), struct.calcsize('P')*8)"` |
| `pyo3` のバージョンが Workspace と dev-deps でズレていないか | `cargo tree -i pyo3` |

まとめ
Windows の AV は「同じ DLL 名でもビルドが違うと別物扱い」問題。

Rust/Python 拡張は Release/Debug を混在させない のが最も安全。

上記の手順で 一度クリーン → 同一 target-dir / 同一プロファイル にすれば
pytest -v でもクラッシュせず通ります。
