// D:\city_chain_project\Algorithm\VRF\vrf_rust_src\src\verifier.rs
// src/verifier.rs
//! VRF proof 検証とハッシュ出力取得

use pyo3::prelude::*;
use vrf::openssl::{ECVRF, CipherSuite};
use vrf::VRF;  // ← トレイトをインポート

#[pyfunction]
pub fn verify_vrf_py(
    public_key: Vec<u8>,
    proof:      Vec<u8>,
    message:    Vec<u8>,
) -> PyResult<Vec<u8>> {
    // 1) ECVRF 初期化
    let mut vrf = ECVRF::from_suite(CipherSuite::P256_SHA256_TAI)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("VRF init error: {:?}", e)))?;

    // 2) proof を検証してハッシュを取得
    let hash = vrf.verify(&public_key, &proof, &message)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("VRF verify error: {:?}", e)))?;

    Ok(hash)
}
