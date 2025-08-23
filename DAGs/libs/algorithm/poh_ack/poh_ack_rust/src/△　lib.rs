// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\src\lib.rs
//! `poh_ack_rust` crate のルートモジュール
//! - ackset: ACK 集合（同期／非同期対応）
//! - ttl: TTL 検証
//! - error: 共通エラー型
//! - bindings: PyO3 バインディング (feature = "python")

pub mod ackset;
pub mod ttl;
pub mod error;

pub use ackset::{Ack, AckSet};
pub use ttl::validate_ttl;
pub use error::AckError;

#[cfg(feature = "python")]
pub mod bindings;

#[cfg(feature = "python")]
use pyo3::prelude::*;

/// PyO3 で Python 拡張として公開されるモジュール（名前は Cargo.toml の lib.name と一致）
#[cfg(feature = "python")]
use pyo3::{prelude::*, Bound, types::PyModule};

#[cfg(feature = "python")]
#[pymodule]
fn poh_ack_rust(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3::prepare_freethreaded_python();
    bindings::init(py, m)
}
