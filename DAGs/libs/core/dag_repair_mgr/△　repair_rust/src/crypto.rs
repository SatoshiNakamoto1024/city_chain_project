use rand::{RngCore, rngs::OsRng};

pub fn dilithium_sign_stub(msg: &str) -> Vec<u8> {
    let mut buf = vec![0u8; 32];
    OsRng.fill_bytes(&mut buf);
    buf.extend(msg.as_bytes());
    buf
}

pub fn dilithium_verify_stub(msg: &str, sig: &[u8]) -> bool {
    if sig.len() < msg.len() { return false; }
    &sig[sig.len() - msg.len()..] == msg.as_bytes()
}
