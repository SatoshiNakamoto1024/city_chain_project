use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use pqcrypto_dilithium::dilithium5::{keypair, sign as pq_sign, open as pq_open};
use pqcrypto_traits::sign::{PublicKey, SecretKey, SignedMessage as _};

#[pyfunction]
fn generate_keypair() -> PyResult<(Vec<u8>, Vec<u8>)> {
    let (pk, sk) = keypair();
    Ok((pk.as_bytes().to_vec(), sk.as_bytes().to_vec()))
}

#[pyfunction]
fn sign(message: &[u8], secret_key: &[u8]) -> PyResult<Vec<u8>> {
    let sk = SecretKey::from_bytes(secret_key)
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid secret key"))?;

    // "SignedMessage" 形式で返ってくる
    let signed_msg = pq_sign(message, &sk);
    // バイナリにして返す
    Ok(signed_msg.as_bytes().to_vec())
}

#[pyfunction]
fn verify(message: &[u8], signed_message: &[u8], public_key: &[u8]) -> PyResult<bool> {
    let pk = PublicKey::from_bytes(public_key)
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid public key"))?;

    // Rustの "SignedMessage" に復元
    let sm = pqcrypto_dilithium::dilithium5::SignedMessage::from_bytes(signed_message)
        .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid signed message"))?;

    // open() で検証 + メッセージ取り出し
    match pq_open(&sm, &pk) {
        Ok(recovered_msg) => {
            // 中身が一致すればOK、違えばNG
            Ok(recovered_msg == message)
        }
        Err(_) => Ok(false),
    }
}

#[pymodule]
fn dilithium5(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(generate_keypair, m)?)?;
    m.add_function(wrap_pyfunction!(sign, m)?)?;
    m.add_function(wrap_pyfunction!(verify, m)?)?;
    Ok(())
}
