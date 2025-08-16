// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\src\utils.rs
use blake2::Blake2bVar;
use blake2::digest::{Update, VariableOutput};

#[inline]
pub fn score_u128(node_id: &str, object_key: &str) -> u128 {
    let mut hasher = Blake2bVar::new(16).unwrap();  // 16-byte digest → BLAKE2b-128相当
    hasher.update(node_id.as_bytes());             // node → key 順に変更
    hasher.update(object_key.as_bytes());
    let mut digest = [0u8; 16];
    hasher.finalize_variable(&mut digest).unwrap();
    u128::from_be_bytes(digest)                   // big-endian に変更
}
