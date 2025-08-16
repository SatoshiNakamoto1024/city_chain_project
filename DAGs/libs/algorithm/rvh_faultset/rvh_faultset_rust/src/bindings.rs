// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\src\bindings.rs

use std::sync::OnceLock;

use pyo3::prelude::*;
use pyo3::types::PyModule;
use pyo3::wrap_pyfunction;
use pyo3::Bound;

use tokio::runtime::Builder;

use crate::faultset::{failover, failover_async};
use crate::error::FaultsetError;

// pyo3-async-runtimes の Tokio 拡張
use pyo3_async_runtimes::tokio::{get_current_locals, future_into_py_with_locals};

/// Rust → Python のエラーマッピング
fn map_err(e: FaultsetError) -> PyErr {
    match e {
        FaultsetError::EmptyNodes => {
            pyo3::exceptions::PyValueError::new_err("node list is empty")
        }
        FaultsetError::LengthMismatch(a, b) => {
            pyo3::exceptions::PyValueError::new_err(format!(
                "nodes length ({}) != latencies length ({})",
                a, b
            ))
        }
        FaultsetError::NegativeThreshold(t) => {
            pyo3::exceptions::PyValueError::new_err(format!(
                "threshold must be non-negative, got {}",
                t
            ))
        }
    }
}

/// 同期版フェイルオーバー
#[pyfunction(name = "failover", text_signature = "(nodes, latencies, threshold, /)")]
fn failover_py(
    nodes: Vec<String>,
    latencies: Vec<f64>,
    threshold: f64,
) -> PyResult<Vec<String>> {
    failover(&nodes, &latencies, threshold).map_err(map_err)
}

/// 非同期版フェイルオーバー
#[pyfunction(name = "failover_async", text_signature = "(nodes, latencies, threshold, /)")]
fn failover_async_py<'py>(
    py: Python<'py>,
    nodes: Vec<String>,
    latencies: Vec<f64>,
    threshold: f64,
) -> PyResult<Bound<'py, PyAny>> {
    // Tokio ランタイムを１回だけ初期化
    ensure_tokio_runtime();

    // **ここがミソ**: Python の asyncio イベントループ情報をキャプチャ
    let locals = get_current_locals(py)?;

    // キャプチャしたローカルを渡して Future→awaitable に変換
    future_into_py_with_locals(py, locals.clone_ref(py), async move {
        failover_async(nodes, latencies, threshold)
            .await
            .map_err(map_err)
    })
}

/// Tokio runtime を一度だけ初期化するヘルパ
fn ensure_tokio_runtime() {
    static RT: OnceLock<()> = OnceLock::new();
    RT.get_or_init(|| {
        let mut builder = Builder::new_multi_thread();
        builder.enable_all();
        pyo3_async_runtimes::tokio::init(builder);
    });
}

/// PyO3 モジュール定義
#[pymodule]
fn rvh_faultset_rust(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // 同期 / 非同期 両方を登録
    m.add_function(wrap_pyfunction!(failover_py, m)?)?;
    m.add_function(wrap_pyfunction!(failover_async_py, m)?)?;
    // バージョン情報
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
