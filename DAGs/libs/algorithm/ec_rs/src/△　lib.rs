// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\lib.rs
use pyo3::prelude::*;

pub mod sharding;

#[pymodule]
fn ec_rust(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sharding::encode_rs_py, m)?)?;
    m.add_function(wrap_pyfunction!(sharding::decode_rs_py, m)?)?;
    Ok(())
}

// Rust ユーザー向けに純粋関数も再公開
pub use sharding::{decode_rs, decode_rs_py, encode_rs, encode_rs_py};
