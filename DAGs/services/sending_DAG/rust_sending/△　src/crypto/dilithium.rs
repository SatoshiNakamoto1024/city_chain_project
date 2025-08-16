// D:\city_chain_project\network\DAGs\sendingDAG\rust_sending\srs\crypto\dilithium.rs
use dilithium5::{sign, verify, generate_keypair};
pub fn sign_message(privkey: &[u8], msg: &[u8]) -> Vec<u8> { /* … */ }
pub fn verify_signature(pubkey: &[u8], msg: &[u8], sig: &[u8]) -> bool { /* … */ }
