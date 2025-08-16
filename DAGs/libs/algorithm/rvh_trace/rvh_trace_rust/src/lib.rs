// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\src\lib.rs

//! rvh_trace_rust: Rust core for tracing & metrics
//!
//! ## Rust Usage
//! ```no_run
//! rvh_trace_rust::init_tracing("info").unwrap();
//! let span = rvh_trace_rust::new_span("example");
//! let _enter = span.enter();
//! tracing::info!("inside span");
//! ```

pub mod trace;
pub mod error;

pub use trace::{init_tracing, new_span, in_span};
pub use error::TraceError;

/* ----------------------------------------------------------------
   Python との橋渡しは bindings.rs に分離している。
   ここでは純粋に Rust API だけをエクスポートする。
---------------------------------------------------------------- */
mod bindings;
pub use bindings::*;          // PyO3 エントリ
#[cfg(feature = "cli")]
pub use bindings::cli_main;

use pyo3::prelude::*;
use pyo3::types::PyAny;
use pyo3::Bound;
use tracing::Level;

/* ========= Python から使う小さな構造体 (ガード) ========= */

#[pyclass]
pub struct PySpanGuard;

#[pymethods]
impl PySpanGuard {
    fn __enter__(&self) {}
    fn __exit__(&self,
        _ty:   &Bound<'_, PyAny>,
        _val:  &Bound<'_, PyAny>,
        _tb:   &Bound<'_, PyAny>,
    ) {}
}

/* ========= Python で `with rvh_trace_rust.span("foo"):` 用 ========= */

#[pyfunction(name = "sync_span")]    // ← Python 側では sync_span になる
fn span(name: &str) -> PyResult<PySpanGuard> {
    let _span  = tracing::span!(Level::INFO, "span", name = name);
    let _enter = _span.enter();
    Ok(PySpanGuard)
}
