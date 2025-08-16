//sending_DAG/rust_sending/dag_core/src/crypto.rs
use rand::{RngCore, rngs::OsRng};

pub fn dilithium_sign_stub(msg: &str) -> Vec<u8> {
    let mut v = vec![0u8; 32];
    OsRng.fill_bytes(&mut v);
    v.extend(msg.as_bytes());
    v
}
