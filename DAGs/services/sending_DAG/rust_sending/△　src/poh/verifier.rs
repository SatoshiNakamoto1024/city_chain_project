use crate::crypto::dilithium;
use super::poh_struct::PoHTx;
pub fn verify_poh(tx: &PoHTx, pubkey: &[u8]) -> bool {
    let msg = format!("{}|{}|{}", tx.tx_id, tx.storage_hash, tx.timestamp);
    dilithium::verify_signature(pubkey, msg.as_bytes(), &tx.signature)
}
