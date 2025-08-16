// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\src\lib.rs

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
