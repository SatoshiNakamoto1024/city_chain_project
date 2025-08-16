use crate::crypto::dilithium;
use super::poh_struct::PoHTx;
pub fn sign_poh(tx: &mut PoHTx, privkey: &[u8]) {
    let msg = format!("{}|{}|{}", tx.tx_id, tx.storage_hash, tx.timestamp);
    tx.signature = dilithium::sign_message(privkey, msg.as_bytes());
}
