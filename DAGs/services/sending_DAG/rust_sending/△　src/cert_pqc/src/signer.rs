//sending_DAG/rust_sending/cert_pqc/src/signer.rs
use pyo3::prelude::*;
use rand::{RngCore, rngs::OsRng};

#[pyfunction]
pub fn dilithium_sign_stub(msg: String, _priv_hex: String) -> Vec<u8> {
    // TODO: real Dilithium impl
    let mut buf = vec![0u8; 32];
    OsRng.fill_bytes(&mut buf);
    buf.extend(msg.as_bytes());
    buf
}
