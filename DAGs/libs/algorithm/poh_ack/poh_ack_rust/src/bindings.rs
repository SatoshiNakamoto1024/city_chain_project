// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\src\bindings.rs
// -----------------------------------------------------------------------------
// src/bindings.rs
// PoH‑ACK ― Rust ↔ Python バインディング（PyO3 0.25 / async‑runtimes 0.25）
// -----------------------------------------------------------------------------

#![cfg(any(feature = "python", feature = "python-ext"))]
// -----------------------------------------------------------------------------
// PoH-ACK ― Rust ↔ Python バインディング（PyO3 0.25 / async-runtimes 0.25）
// -----------------------------------------------------------------------------

use chrono::{DateTime, Utc};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use pyo3::{types::PyModule, Bound};
use pyo3_async_runtimes::tokio::future_into_py;

use crate::{Ack, AckError, AckSet, validate_ttl};

/// Rust → Python 例外変換
impl From<AckError> for PyErr {
    fn from(e: AckError) -> Self {
        PyValueError::new_err(e.to_string())
    }
}

// ===========================================================================
// Python 側に公開する 1 件 ACK ラッパ ― PyAck
// ===========================================================================
#[pyclass(name = "Ack")]
#[derive(Clone)]
pub struct PyAck {
    inner: Ack,
}

#[pymethods]
impl PyAck {
    /// `PyAck(id, timestamp_rfc3339, signature_b58, pubkey_b58)`
    #[new]
    fn new(id: String, timestamp: &str, signature: String, pubkey: String) -> PyResult<Self> {
        let ts: DateTime<Utc> = timestamp
            .parse()
            .map_err(|e| PyValueError::new_err(format!("invalid timestamp: {e}")))?;
        Ok(Self {
            inner: Ack { id, timestamp: ts, signature, pubkey },
        })
    }

    /// 同期検証（署名＋TTL）
    fn verify(&self, ttl_sec: i64) -> PyResult<()> {
        self.inner.verify(ttl_sec).map_err(Into::into)
    }

    /// 非同期検証
    fn verify_async<'py>(
        &self,
        py: Python<'py>,
        ttl_sec: i64,
    ) -> PyResult<Bound<'py, PyAny>> {
        let ack = self.inner.clone();
        future_into_py(py, async move {
            ack.verify(ttl_sec)
                .map_err(|e| PyValueError::new_err(e.to_string()))?;
            Ok(())
        })
    }

    // プロパティ
    #[getter]
    fn id(&self) -> String { self.inner.id.clone() }

    #[getter]
    fn timestamp(&self) -> String { self.inner.timestamp.to_rfc3339() }
}

// ===========================================================================
// Python 側に公開する ACK 集合ラッパ ― PyAckSet
// ===========================================================================
#[pyclass(name = "AckSet")]
#[derive(Clone)]
pub struct PyAckSet {
    inner: AckSet,
}

#[pymethods]
impl PyAckSet {
    #[new]
    fn new() -> Self {
        Self { inner: AckSet::new() }
    }

    /// 同期追加＋検証
    fn add(&mut self, ack: &PyAck, ttl_sec: i64) -> PyResult<()> {
        self.inner.add(ack.inner.clone(), ttl_sec).map_err(Into::into)
    }

    /// 非同期追加＋検証
    fn add_async<'py>(
        &self,
        py: Python<'py>,
        ack: &PyAck,
        ttl_sec: i64,
    ) -> PyResult<Bound<'py, PyAny>> {
        let mut set = self.inner.clone();
        let ack     = ack.inner.clone();
        future_into_py(py, async move {
            set.add(ack, ttl_sec)
                .map_err(|e| PyValueError::new_err(e.to_string()))?;
            Ok(())
        })
    }

    /// 格納済み ID 一覧
    fn ids(&self) -> Vec<String> {
        self.inner.ids()
    }
}

// ===========================================================================
// TTL チェックだけが欲しいときのユーティリティ関数
// ===========================================================================
#[pyfunction]
fn check_ttl(ts: &str, ttl_sec: i64) -> PyResult<bool> {
    let parsed: DateTime<Utc> = ts
        .parse()
        .map_err(|e| PyValueError::new_err(format!("invalid timestamp: {e}")))?;
    Ok(validate_ttl(&parsed, ttl_sec).is_ok())
}

// ===========================================================================
// lib.rs から呼ばれる初期化関数
// ===========================================================================
pub fn init(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyAck>()?;
    m.add_class::<PyAckSet>()?;
    m.add_function(wrap_pyfunction!(check_ttl, m)?)?;
    Ok(())
}
