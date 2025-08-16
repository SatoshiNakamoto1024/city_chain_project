// D:\city_chain_project\Algorithm\VRF\vrf_rust_src\src\keypair.rs
// src/keypair.rs

//! VRF 鍵ペア生成（OpenSSL の P-256 + ECVRF）
//! Python から呼び出せる generate_vrf_keypair_py 関数を提供

use pyo3::prelude::*;
use vrf::openssl::{ECVRF, CipherSuite};
use openssl::ec::{EcGroup, EcKey};
use openssl::nid::Nid;

#[pyfunction]
/// VRF 用の鍵ペアを生成して (public_key_bytes, secret_key_bytes) を返す
pub fn generate_vrf_keypair_py() -> PyResult<(Vec<u8>, Vec<u8>)> {
    // 1) EC キー生成 (NIST P-256)
    let group = EcGroup::from_curve_name(Nid::X9_62_PRIME256V1)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("EC group error: {:?}", e),
        ))?;
    let ec_key = EcKey::generate(&group)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("EC key generation error: {:?}", e),
        ))?;

    // 2) 秘密鍵をビッグエンディアンバイト列で取得
    let sk_bytes = ec_key.private_key().to_vec();

    // 3) ECVRF コンテキスト初期化 (P256_SHA256_TAI)
    let mut vrf = ECVRF::from_suite(CipherSuite::P256_SHA256_TAI)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("VRF init error: {:?}", e),
        ))?;

    // 4) VRF derive_public_key で公開鍵を取得
    let pk_bytes = vrf.derive_public_key(&sk_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("derive_public_key error: {:?}", e),
        ))?;

    Ok((pk_bytes, sk_bytes))
}
