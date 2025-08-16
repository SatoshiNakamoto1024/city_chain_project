// D:\city_chain_project\Algorithm\VRF\vrf_rust_src\src\keypairs.rs
//! VRF 鍵ペア生成（OpenSSL の P-256 + ECVRF）
//! PublicKey, SecretKey は共にビッグエンディアンバイト列

use pyo3::prelude::*;
use vrf::openssl::{ECVRF, CipherSuite};
use openssl::ec::{EcGroup, EcKey};
use openssl::nid::Nid;

/// Dilithium の代わりに ECVRF（P-256）を利用
/// - 署名ではなく VRF proof を使う
/// - `derive_public_key` で公開鍵を取得
#[pyfunction]
pub fn generate_vrf_keypair_py() -> PyResult<(Vec<u8>, Vec<u8>)> {
    // 1) EC キー生成 (NIST P-256)
    let group = EcGroup::from_curve_name(Nid::X9_62_PRIME256V1)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("EC group error: {:?}", e)))?;
    let ec_key = EcKey::generate(&group)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("EC key generate error: {:?}", e)))?;

    // 2) 秘密鍵をビッグエンディアンバイト列で取得
    let sk_bytes = ec_key.private_key().to_vec();

    // 3) ECVRF コンテキスト初期化 (P256_SHA256_TAI)
    let mut vrf = ECVRF::from_suite(CipherSuite::P256_SHA256_TAI)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("VRF init error: {:?}", e)))?;

    // 4) VRF derive_public_key で公開鍵を取得
    let pk_bytes = vrf.derive_public_key(&sk_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("derive_public_key error: {:?}", e)))?;

    Ok((pk_bytes, sk_bytes))
}
