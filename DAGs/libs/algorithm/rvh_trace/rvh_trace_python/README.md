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


#　以下、rvh_trace_python の機能概要と使い方をまとめました。



#　ビルドが先
D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_python>pip install -e .
Successfully built rvh_trace rvh_trace_rust
Installing collected packages: rvh_trace_rust, rvh_trace
  Attempting uninstall: rvh_trace_rust
    Found existing installation: rvh_trace_rust 0.1.0
    Uninstalling rvh_trace_rust-0.1.0:
      Successfully uninstalled rvh_trace_rust-0.1.0
  Attempting uninstall: rvh_trace
    Found existing installation: rvh_trace 0.1.0
    Uninstalling rvh_trace-0.1.0:
      Successfully uninstalled rvh_trace-0.1.0
Successfully installed rvh_trace-0.1.0 rvh_trace_rust-0.1.0
Installing collected packages: rvh_trace
Successfully installed rvh_trace-0.1.0

#　wheel を dist\ に置きたいなら
python -m build --wheel --outdir dist（Python ラッパも含め全部）

先に Rust拡張 を入れる（これが無いと rvh_trace_python の依存解決で転ぶ）
# レポジトリ ルートで
maturin develop \
  -m DAGs/libs/algorithm/rvh_trace/rvh_trace_rust/Cargo.toml \
  --features python \
  --release

python -c "import rvh_trace_rust; print('rust ext OK')"


#　テスト方法
# ② またはディレクトリに入って
cd DAGs/libs/algorithm/rvh_trace/rvh_trace_python
pip install -e '.[test]'

# CLI 動作確認
$ python -m rvh_trace.app_trace --level debug --name demo
step 0
step 1
step 2

# 単体テスト
$ pytest rvh_trace_python/tests -q
......
8 passed in 0.42s


(.venv312) D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_python>pytest -v rvh_trace/tests
================================================= test session starts =================================================
platform win32 -- Python 3.12.10, pytest-8.4.1, pluggy-1.6.0 -- D:\city_chain_project\.venv312\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\city_chain_project
configfile: pyproject.toml
plugins: anyio-4.9.0, asyncio-1.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 3 items

rvh_trace\tests\test_trace.py::test_async_span_records PASSED                                                    [ 33%]
rvh_trace\tests\test_trace.py::test_sync_trace_decorator PASSED                                                  [ 66%]
rvh_trace\tests\test_trace.py::test_trace_decorator_async PASSED                                                 [100%]

================================================== 3 passed in 0.13s ==================================================

