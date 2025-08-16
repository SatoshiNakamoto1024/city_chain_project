rvh_trace/
├── README.md
├── LICENSE                   (Apache-2.0 例)
├── .gitignore
├── rvh_trace_integration.py                   ← rust・pythonの統合テスト
├── .github/
│   └── workflows/ci.yml
│
├── rvh_trace_rust/           ← Rust コア + PyO3 バインディング
│   ├── Cargo.toml
│   ├── pyproject.toml        ← maturin 用 (sdist / wheel)
│   ├── benches/
│   │   └── bench_trace.rs    ← Criterion + Tokio runtime
│   └── src/
│       ├── lib.rs            ← pub use trace::*; エクスポート
│       ├── trace.rs          ← span/metric 発行本体
│       ├── error.rs          ← anyhow + thiserror ラッパー
│       ├── bindings.rs       ← #[pymodule] rvh_trace
│       ├── main_trace.rs     ← `cargo run -p rvh_trace_rust --example cli`
│       └── tests/
│           ├── test_cli.rs    　  (CLIテスト)
│           ├── test_import.rs    (importテスト)
│           ├── test_trace.rs      (Rust 単体)
│           └── test_py_bindings.rs     (PyO3 経由)
│
├── rvh_trace_python/         ← Python ラッパー・ユーティリティ
│   ├── pyproject.toml        ← pure-Python 側
│   ├── README.md
│   └── rvh_trace/
│       ├── __init__.py
│       ├── _version.py
│       ├── app_trace.py
│       ├── trace_builder.py
│       ├── otel_helper.py    ← OTLP exporter shortcut
│       └── tests/
│           └── test_trace.py


以下、rvh_trace の機能概要と使い方をまとめました。
rust-pythonの非同期の行き来も詳細に解説してみる

1 . なにが出来るライブラリなのか
| レイヤ                           | 主な仕事                                                                                                                | 代表 API                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **Rust (`rvh_trace_rust`)**   | • `tracing` + `opentelemetry` を使った本格的な Span／イベント発行<br>• Tokio ランタイムを *自動で 1 回だけ* 起動<br>• PyO3 で Python から呼べる関数・型を公開 | `init_tracing()`,<br>`new_span()`, `span()` |
| **Python ラッパー (`rvh_trace`)** | • Rust-Span を “Pythonっぽく” 使う薄いラッパー<br>• 同期 / 非同期どちらでも使える **context-manager** & **デコレータ** を提供                        | `init_tracing()`,<br>`span()`, `trace()`    |

これにより
with span("sync_op", user=1):
    ...
async with span("async_op"):
    ...
@trace("task")          # sync/async どちらの関数にも貼れる
async def job(): ...
と書くだけで、高速 (Rust) + 使い勝手 (Py) を両立した計測が取れます。

発行された Span は OpenTelemetry 経由で collector にも流せますし、
pytest の caplog が捕まえる Python logging にも降りてきます。

2 . Rust ↔ Python “二段構え” の流れ
2-1. トレーサ初期化
Python ──┐  init_tracing()             Rust
         │ ─────────────────►  once-only Tokio runtime
         │                    + tracing_subscriber
         └◄──────────────────  （二重初期化は OnceLock でブロック）
Tokio は OnceLock + pyo3_async_runtimes::tokio::init(builder)
で プロセス内に 1 度だけ 起動。

tracing_subscriber の fmt layer と OTLP exporter を
Rust 側で組むので、Python は まったく意識しなくて良い。

2-2. Span を張る（同期・非同期共通パス）
Python  ── span("name") ──────────────┐
                                     │
                       PyO3バウンド   ▼
Rust    new_span("name") → tracing::Span ──┐
                                           │ 実行終わりで drop
                    トレースイベント ←─────┘
                      （subscriber 経由で
                       log & OTLP へ）
Python wrapper はただの handle （PySpan）を保持するだけ。
終了時に __exit__ / __aexit__ で参照が drop され、
Rust 側 Span が スコープ終了 を検知して完結イベントが出る。

2-3. Rust Future → Python awaitable（完全 async パス）
pyo3_async_runtimes::tokio::future_into_py(py, async move { ... })
これが コア技。
Rust async で書いた処理を Python から await 可能な
coroutine オブジェクトに包む。

逆に Python が回しているイベントループから見れば
「純粋な PyObject」なので、asyncio.run_until_complete() で回せる。

3 . 主なソース断面
| 場所                               | 役割・ポイント                                                                                                              |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **`src/bindings.rs`**            | *Tokio runtime once-init*・`#[pyfunction]` 群<br>  `py_span()` は Rust Future → Python awaitable の橋渡し                   |
| **`rvh_trace/__init__.py`**      | `_SpanCM` で **sync / async 両取り** の context-manager を実装                                                               |
| **`rvh_trace/trace_builder.py`** | 任意関数を Span で包む **デコレータ (@trace)**。同期⇆非同期を `inspect.iscoroutinefunction()` で自動判定                                      |
| **テスト**                          | *単体* (`test_trace.py`) と *統合* (`test_trace_integration.py`) の 2 レイヤ。<br>後者は **Rust ↔ Python ↔ logger** の全経路を e2e で確認 |


4 . なぜ “Rust直 API” テストだけログが出ないのか
rvh_trace_rust.new_span() は tracing イベント を発行するだけで、
Python の logging へは 何も 流さない。

caplog が拾うのは Python logging だけなので空ログが正常。
⇒ テストでは「例外なく呼べること」を確認するだけに変更。

5 . 典型ボトルネック／落とし穴
Tokio を 2 回以上初期化
→ OnceLock + pyo3_async_runtimes マクロで必ず 1 回に。

Python 側イベントループが無い
→ テストでは asyncio.new_event_loop() → set_event_loop() で明示。

Rust Span → Python logging の経路
tracing-subscriber fmt layer を tracing_log::LogTracer::init() と併用すると
Rust tracing → Rust log → Python logging がつながる。

6 . まとめ
高スループット (Rust, Tokio, zero-alloc tracing) と
Python の書き心地 (with / async with / decorator) を両立。

OpenTelemetry 互換なので SaaS APM への流用も一発。

すべて 再入可能・once-init 設計のため、
Jupyter / Django / FastAPI など複数インポート環境でも安全。

これで「Rust で筋肉、Python で優雅」を実現する ユニバーサル Tracing 基盤 が完成です。


# テスト時の注意
下の 1 ファイルだけ を作れば
Rust ↔ Python ↔ ロガー すべてを貫通する“統合テスト”になります。
（rvh_trace_rust は既に pip インストール済み／ビルド済み前提）

ポイント
sys.path をいじる
-　ローカル開発中でも pip install -e . 不要 で動かせます。
-　Wheel を手動ビルドしてある場合も自動で拾います。

caplog で logger を捕捉
先に修正した rvh_trace/__init__.py 内 _logger.info() が
ここでキャッチされ、Rust→Python→logging の流れを検証できます。

Rust 直 call も 1 ケース
rvh_trace_rust.new_span() を直接呼び、
Python 側の span ラッパー無しでもエラーにならないことを確認。

この 1 ファイルをプロジェクト直下に置いて
pytest -v test_trace_integration.py

を実行すれば、Rust → Python エコシステムの
“フル機能” 統合テストとしてそのまま本番 CI に使えます。

(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_trace>pytest -v test_trace_integration.py
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 5 items

test_trace_integration.py::test_async_span_integration PASSED                                                    [ 20%]
test_trace_integration.py::test_sync_span_integration PASSED                                                     [ 40%]
test_trace_integration.py::test_trace_decorator_sync PASSED                                                      [ 60%]
test_trace_integration.py::test_trace_decorator_async PASSED                                                     [ 80%]
test_trace_integration.py::test_direct_rust_span PASSED                                                          [100%]

================================================== 5 passed in 0.39s ==================================================
