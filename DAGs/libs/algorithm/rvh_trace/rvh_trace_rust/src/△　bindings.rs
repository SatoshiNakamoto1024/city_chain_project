// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\src\bindings.rs
// -----------------------------------------------------------------------------
// src/bindings.rs
// -----------------------------------------------------------------------------
// PyO3 でビルドされる Python モジュール側のエントリポイント。
// - sync_span … `with rvh_trace_rust.sync_span("foo"):` で使う同期版
// - span      … `await rvh_trace_rust.span("foo")`      で使う非同期版
// -----------------------------------------------------------------------------

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};
use pyo3::wrap_pyfunction;
use pyo3::Bound;

// ───── Tokio ランタイムを “一度だけ” 用意する ─────
use std::sync::OnceLock;              // Rust 1.70 以降の std 補完型 
use tokio::runtime::Builder;          // ランタイムのビルダー

static TOKIO_RT_INIT: OnceLock<()> = OnceLock::new();

/// 最初の 1 回だけ pyo3-async-runtimes で Tokio を登録する
fn init_tokio_once() {
    TOKIO_RT_INIT.get_or_init(|| {
        // Builder → enable_all で I/O & timer を有効化 :contentReference[oaicite:1]{index=1}
        let mut builder = Builder::new_multi_thread();
        builder.enable_all();
        pyo3_async_runtimes::tokio::init(builder);      // init(Builder) のシグネチャ :contentReference[oaicite:2]{index=2}
    });
}


use crate::{
    init_tracing as init_tracing_rs,
    new_span,
    span as sync_span_impl,   // lib.rs にある同期版 span（Rust ⇒ Py ガード返却）
    PySpanGuard,
};

/* ───────────────────────── Python から呼ぶ関数 ───────────────────────── */

/// Python 側から Rust のトレーシングを初期化
///
/// ```python
/// import rvh_trace_rust as trace
/// trace.init_tracing("debug")
/// ```
#[pyfunction(name = "init_tracing")]
fn py_init_tracing(level: &str) -> PyResult<()> {
    init_tokio_once(); 
    init_tracing_rs(level)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

/// 同期版：`with rvh_trace_rust.sync_span("foo"):`
///
/// Python から見ると “ガードオブジェクト（コンテキストマネージャ）” が返る。
#[pyfunction(name = "sync_span")]
fn sync_span(name: &str) -> PyResult<PySpanGuard> {
    // Rust 側に実装済みの span 関数をそのまま呼び出す
    init_tokio_once(); 
    sync_span_impl(name)
}

/// 非同期版：`await rvh_trace_rust.span("foo", key="val")`
#[pyfunction(name = "span", signature = (name, kwargs = None))]
fn py_span<'py>(
    py: Python<'py>,
    name: &str,
    kwargs: Option<&Bound<'py, PyDict>>,
) -> PyResult<Bound<'py, PyAny>> {
    /* 1) Rust 側の span を開始 */
    init_tokio_once(); 
    let span = new_span(name);

    /* 2) 追加フィールドを kwargs から記録 */
    if let Some(kvs) = kwargs {
        for (k, v) in kvs {
            span.record(k.extract::<&str>()?, v.extract::<&str>()?);
        }
    }

    /* 3) Future を Python awaitable として返す */
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        drop(span);                              // Future 終了時に span を閉じる
        Python::with_gil(|py| Ok(py.None()))     // 戻り値は None
    })
}

/* ────────────────────────── PyO3 モジュール定義 ───────────────────────── */

#[pymodule]
fn rvh_trace_rust(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    init_tokio_once();                    // ★ ここを追加 ★
    
    // with …: 用（同期）
    m.add_function(wrap_pyfunction!(sync_span, m)?)?;
    // await …: 用（非同期）
    m.add_function(wrap_pyfunction!(py_span,   m)?)?;
    // 初期化
    m.add_function(wrap_pyfunction!(py_init_tracing, m)?)?;
    // ガード型
    m.add_class::<PySpanGuard>()?;
    Ok(())
}

/* ─────────────────────── optional: CLI entrypoint ─────────────────────── */

#[cfg(feature = "cli")]
#[pyfunction]
fn cli_main_py() -> PyResult<()> {
    crate::bindings::cli_main()
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}
