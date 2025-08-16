// D:\city_chain_project\Algorithm\VRF\vrf_rust_src\src\prover.rs
// src/prover.rs
//! VRF proof（π）生成とハッシュ出力

use pyo3::prelude::*;
use vrf::openssl::{ECVRF, CipherSuite};
use vrf::VRF;  // ← トレイトをインポート

#[pyfunction]
pub fn prove_vrf_py(secret_key: Vec<u8>, message: Vec<u8>) -> PyResult<(Vec<u8>, Vec<u8>)> {
    // 1) ECVRF 初期化
    let mut vrf = ECVRF::from_suite(CipherSuite::P256_SHA256_TAI)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("VRF init error: {:?}", e)))?;

    // 2) proof π を生成
    let proof = vrf.prove(&secret_key, &message)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("VRF prove error: {:?}", e)))?;

    // 3) proof からハッシュを計算
    let hash = vrf.proof_to_hash(&proof)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("proof_to_hash error: {:?}", e)))?;

    Ok((proof, hash))
}
