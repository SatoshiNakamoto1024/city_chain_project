// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\src\bindings.rs
//! PyO3 で Python へ公開する FFI ラッパ
//! --------------------------------------
//! import rvh_rust
//! rvh_rust.rendezvous_hash(["node1","node2"], "obj-123", 1)

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use indoc::indoc;                     // ← 追加
use crate::rendezvous::{rendezvous_hash, RendezvousError};  // ← 型名修正

/// Python から呼べる HRW ハッシュ
#[pyfunction(name = "rendezvous_hash")]          // ← ここを追加
#[pyo3(text_signature = "(nodes, key, k, /)")]
fn rendezvous_hash_py(
    nodes: Vec<String>,
    key:   String,
    k:     usize,
) -> PyResult<Vec<String>> {
    rendezvous_hash(&nodes, &key, k).map_err(|e| match e {
        RendezvousError::NoNodes          =>
            pyo3::exceptions::PyValueError::new_err("nodes is empty"),

        RendezvousError::TooMany(k, n)    =>
            pyo3::exceptions::PyValueError::new_err(format!("k={k} > n={n}")),
    })
}

/// Python モジュール初期化
#[pymodule]
fn rvh_rust(py: Python<'_>, m: &PyModule) -> PyResult<()> {
    // 関数を登録
    m.add_function(wrap_pyfunction!(rendezvous_hash_py, m)?)?;

    // バージョン文字列を埋め込む（build.rs で生成しても OK）
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // docstring
    let doc = indoc::indoc! { r#"
        rvh_rust
        ========
        高速 Rendezvous/HRW Hashing - Rust 実装

        >>> import rvh_rust
        >>> rvh_rust.rendezvous_hash(["n1","n2","n3"], "key42", 2)
        ['n3', 'n1']
    "#};
    m.add("__doc__", doc)?;

    // バックグラウンドで GIL を解放できるようにフック（必要なら）
    pyo3::prepare_freethreaded_python();

    Ok(())
}
