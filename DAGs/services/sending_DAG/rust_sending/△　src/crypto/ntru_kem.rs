use ntrust_native::{crypto_kem_keypair, crypto_kem_enc, crypto_kem_dec, AesState};
pub fn encapsulate(pubkey: &[u8]) -> (Vec<u8>, Vec<u8>) { /* … */ }
pub fn decapsulate(cipher: &[u8], seckey: &[u8]) -> Vec<u8> { /* … */ }
