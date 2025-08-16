// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\src\bindings.rs
use pyo3::prelude::*;
use pyo3::types::PyModule;
use pyo3::wrap_pyfunction;
use pyo3::Bound;                     // ★ 追加
use crate::rendezvous::{rendezvous_hash, rendezvous_hash_async, RendezvousError};
use indoc::indoc;

// エラー → PyErr 変換ヘルパ
fn map_err(e: RendezvousError) -> PyErr {
    match e {
        RendezvousError::NoNodes => pyo3::exceptions::PyValueError::new_err("nodes is empty"),
        RendezvousError::TooMany(k, n) => {
            pyo3::exceptions::PyValueError::new_err(format!("k {k} > nodes {n}"))
        }
    }
}

/// 同期版
#[pyfunction(name = "rendezvous_hash", text_signature = "(nodes, key, k, /)")]
fn rendezvous_hash_py(
    nodes: Vec<String>,
    key: String,
    k:   usize,
) -> PyResult<Vec<String>> {
    rendezvous_hash(&nodes, &key, k).map_err(map_err)
}

/// 非同期版
#[pyfunction(name = "rendezvous_hash_async", text_signature = "(nodes, key, k, /)")]
fn rendezvous_hash_async_py<'py>(
    py: Python<'py>,
    nodes: Vec<String>,
    key:   String,
    k:     usize,
) -> PyResult<Bound<'py, PyAny>> {
    ensure_tokio_runtime();
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        rendezvous_hash_async(nodes, key, k).await.map_err(map_err)
    })
}

/// **Tokio ランタイムを 1 回だけ初期化** — PyO3 0.25
fn ensure_tokio_runtime() {
    use std::sync::OnceLock;
    static RT: OnceLock<()> = OnceLock::new();
    RT.get_or_init(|| {
        // pyo3-async-runtimes 0.25: `init(builder)` に変わりました
        let mut builder = tokio::runtime::Builder::new_multi_thread();
        builder.enable_all();
        pyo3_async_runtimes::tokio::init(builder);
    });
}

/// PyO3 モジュール
#[pymodule]
fn rvh_core_rust(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // 関数登録
    m.add_function(wrap_pyfunction!(rendezvous_hash_py, m)?)?;
    m.add_function(wrap_pyfunction!(rendezvous_hash_async_py, m)?)?;

    // 定数・ドキュメント
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add(
        "__doc__",
        indoc! {r#"
        rvh_core_rust
        =============
        高速 Rendezvous / HRW Hashing （Rust + PyO3 バインディング）

        >>> import rvh_core_rust as rvh
        >>> rvh.rendezvous_hash(["n1","n2","n3"], "key42", 2)
        ['n3', 'n1']
        "#},
    )?;

    Ok(())
}
