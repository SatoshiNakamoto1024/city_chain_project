// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\bindings.rs
use pyo3::prelude::*;
use crate::sharding;
use crate::metrics;

/// Python module definition
#[pymodule]
fn ec_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(encode_shards_py, m)?)?;
    m.add_function(wrap_pyfunction!(decode_shards_py, m)?)?;
    m.add_function(wrap_pyfunction!(status_py, m)?)?;
    Ok(())
}

#[pyfunction]
fn encode_shards_py(
    data: Vec<u8>,
    data_shards: usize,
    parity_shards: usize,
) -> PyResult<Vec<Vec<u8>>> {
    sharding::encode_shards(&data, data_shards, parity_shards)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn decode_shards_py(
    shards: Vec<Option<Vec<u8>>>,
    data_shards: usize,
    parity_shards: usize,
) -> PyResult<Vec<u8>> {
    sharding::decode_shards(shards, data_shards, parity_shards)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn status_py() -> PyResult<String> {
    let enc = metrics::get_encode_time();
    let dec = metrics::get_decode_time();
    Ok(format!("encode_time_ns: {}, decode_time_ns: {}", enc, dec))
}
