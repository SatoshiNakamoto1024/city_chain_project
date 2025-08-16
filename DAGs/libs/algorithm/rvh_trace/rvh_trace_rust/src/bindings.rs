// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\src\bindings.rs
// -----------------------------------------------------------------------------
// src/bindings.rs
// Rust-⇔-Python のブリッジ（Pyo3）
// -----------------------------------------------------------------------------

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};
use pyo3::wrap_pyfunction;
use pyo3::{Bound, Py};

use std::sync::OnceLock;
use tokio::runtime::Builder;

// ─── Tokio ランタイムは 1 度だけ初期化 ──────────────────────────────
static TOKIO_RT_INIT: OnceLock<()> = OnceLock::new();

fn init_tokio_once() {
    TOKIO_RT_INIT.get_or_init(|| {
        let mut builder = Builder::new_multi_thread();
        builder.enable_all();
        pyo3_async_runtimes::tokio::init(builder);
    });
}

// ─── クレート内の公開シンボルを再利用 ───────────────────────────────
use crate::{
    init_tracing as init_tracing_rs,
    new_span as rs_new_span,
    span as sync_span_impl,
    PySpanGuard,
};

// ← ここを tracing 版に変更
use tracing::Span as InnerSpan;

// -----------------------------------------------------------------------------
// Python 側で使える Span ラッパ
// -----------------------------------------------------------------------------
#[pyclass(name = "Span")]
#[derive(Debug)]
pub struct PySpan {
    inner: InnerSpan,
}

#[pymethods]
impl PySpan {
    /// キー／値を追記
    fn record(&self, key: &str, value: &str) {
        self.inner.record(key, value);
    }

    /// __repr__
    fn __repr__(&self) -> PyResult<String> {
        Ok(format!("<Span {:?}>", self.inner))
    }
}

// -----------------------------------------------------------------------------
// Python から呼ばれる関数
// -----------------------------------------------------------------------------
#[pyfunction(name = "init_tracing")]
fn py_init_tracing(level: &str) -> PyResult<()> {
    init_tokio_once();
    init_tracing_rs(level)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction(name = "new_span")]
fn py_new_span(py: Python<'_>, name: &str) -> PyResult<Py<PySpan>> {
    init_tokio_once();
    let span = rs_new_span(name);
    let py_span = Py::new(py, PySpan { inner: span })?;   // ← Ok(...) でラップ
    Ok(py_span)
}

#[pyfunction(name = "sync_span")]
fn sync_span(name: &str) -> PyResult<PySpanGuard> {
    init_tokio_once();
    sync_span_impl(name)
}

#[pyfunction(name = "span", signature = (name, kwargs = None))]
fn py_span<'py>(
    py: Python<'py>,
    name: &str,
    kwargs: Option<&Bound<'py, PyDict>>,
) -> PyResult<Bound<'py, PyAny>> {
    init_tokio_once();

    let span = rs_new_span(name);
    if let Some(kvs) = kwargs {
        for (k, v) in kvs {
            span.record(k.extract::<&str>()?, v.extract::<&str>()?);
        }
    }

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        drop(span);
        Python::with_gil(|py| Ok(py.None()))
    })
}

// -----------------------------------------------------------------------------
// PyO3 モジュール定義
// -----------------------------------------------------------------------------
#[pymodule]
fn rvh_trace_rust(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    init_tokio_once();

    // 低レベル API
    m.add_class::<PySpan>()?;
    m.add_function(wrap_pyfunction!(py_new_span, m)?)?;

    // 高レベル API
    m.add_function(wrap_pyfunction!(py_init_tracing, m)?)?;
    m.add_function(wrap_pyfunction!(sync_span,      m)?)?;
    m.add_function(wrap_pyfunction!(py_span,        m)?)?;

    // with ... 用ガード
    m.add_class::<PySpanGuard>()?;
    Ok(())
}

// ─── optional CLI entrypoint ────────────────────────────────────────────────
#[cfg(feature = "cli")]
#[pyfunction]
fn cli_main_py() -> PyResult<()> {
    crate::bindings::cli_main()
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}
