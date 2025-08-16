// D:\city_chain_project\Algorithm\VRF\vrf_rust_src\src\lib.rs
// src/lib.rs

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

pub mod keypair;
pub mod prover;
pub mod verifier;

/// Python モジュール初期化関数
#[pymodule]
fn vrf_rust(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    // Rust 側で実装した関数を Python から呼び出せるように登録
    m.add_function(wrap_pyfunction!(keypair::generate_vrf_keypair_py, m)?)?;
    m.add_function(wrap_pyfunction!(prover::prove_vrf_py, m)?)?;
    m.add_function(wrap_pyfunction!(verifier::verify_vrf_py, m)?)?;
    Ok(())
}
