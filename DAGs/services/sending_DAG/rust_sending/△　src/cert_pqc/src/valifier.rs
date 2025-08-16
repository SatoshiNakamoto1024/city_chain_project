//sending_DAG/rust_sending/cert_pqc/src/varifier.rs
use pyo3::prelude::*;

/// ダミー Dilithium 検証：msg が sig の後ろに埋め込んであれば OK
#[pyfunction]
pub fn dilithium_verify_stub(msg: String, sig: Vec<u8>, _pub_hex: String) -> bool {
    if sig.len() < msg.len() { return false; }
    let tail = &sig[sig.len() - msg.len()..];
    tail == msg.as_bytes()
}
