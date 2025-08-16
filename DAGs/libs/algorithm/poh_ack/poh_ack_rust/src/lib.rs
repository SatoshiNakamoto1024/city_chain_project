// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\src\lib.rs

//! `poh_ack_rust` crate のルートモジュール
//! - ackset: ACK 集合（同期／非同期対応）
//! - ttl: TTL 検証
//! - error: 共通エラー型
//! - bindings: PyO3 バインディング
//!
//!  ⚠  PyO3 拡張を含めてビルドする feature は
//!     * python        … maturin develop / pytest 用
//!     * python-ext    … wheel-build 用
//!     * python-embed  … cargo test 用
//!     の 3 種を許容する。

pub mod ackset;
pub mod ttl;
pub mod error;

pub use ackset::{Ack, AckSet};
pub use ttl::validate_ttl;
pub use error::AckError;

/* ────────────────────────────────────────────────────────────────
   PyO3 バインディングは python / python-ext のどちらかが立っていれば
   コンパイルする（python-embed は python を継承するので OK）
   ──────────────────────────────────────────────────────────── */
#[cfg(any(feature = "python", feature = "python-ext"))]
pub mod bindings;

#[cfg(any(feature = "python", feature = "python-ext"))]
use pyo3::{prelude::*, Bound, types::PyModule};

/// `poh_ack_rust` として Python から import されるモジュール
#[cfg(any(feature = "python", feature = "python-ext"))]
#[pymodule]
fn poh_ack_rust(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    bindings::init(py, m)
}
