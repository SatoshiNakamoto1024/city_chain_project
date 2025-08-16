// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\src\utils.rs
//! Rendezvous ハッシュ向けユーティリティ

use blake2::{Blake2b512, Digest};

/// node_id + key → 128-bit スコア
#[inline]
pub fn score_u128(node_id: &str, object_key: &str) -> u128 {
    let mut hasher = Blake2b512::new();
    hasher.update(node_id.as_bytes());
    hasher.update(object_key.as_bytes());
    let digest = hasher.finalize();
    let mut bytes = [0u8; 16];
    bytes.copy_from_slice(&digest[..16]);
    u128::from_be_bytes(bytes)
}
