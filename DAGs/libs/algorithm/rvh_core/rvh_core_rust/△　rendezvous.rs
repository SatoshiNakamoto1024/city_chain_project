// D:\city_chain_project\DAGs\libs\algorithm\rvh_core\rvh_core_rust\src\rendezvous.rs

use blake2::Blake2b512;
use blake2::Digest;
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Errors returned by rendezvous_hash
#[derive(Debug, thiserror::Error)]
pub enum RendezvousError {
    #[error("No nodes provided")]
    NoNodes,
    #[error("Requested k ({0}) exceeds node count ({1})")]
    TooMany(usize, usize),
}

/// Compute the Rendezvous (Highest‐Random‐Weight) hash.
///
/// # Arguments
/// * `nodes` - slice of node identifiers
/// * `key`   - the key (e.g. object ID) to hash
/// * `k`     - number of nodes to select
///
/// # Returns
/// A Vec<String> of the top‐k selected node IDs, or an error.
pub fn rendezvous_hash(
    nodes: &[String],
    key: &str,
    k: usize,
) -> Result<Vec<String>, RendezvousError> {
    if nodes.is_empty() {
        return Err(RendezvousError::NoNodes);
    }
    if k > nodes.len() {
        return Err(RendezvousError::TooMany(k, nodes.len()));
    }

    // Compute scores
    let mut scores: Vec<(u128, &String)> = nodes
        .iter()
        .map(|node| {
            let mut hasher = Blake2b512::new();
            hasher.update(node.as_bytes());
            hasher.update(key.as_bytes());
            let hash = hasher.finalize(); // GenericArray<u8, U64> として確定
            let mut bytes = [0u8; 16];
            bytes.copy_from_slice(&hash[..16]);
            let score = u128::from_be_bytes(bytes);
            (score, node)
        })
        .collect();

    // Sort descending and pick top-k
    scores.sort_by(|a, b| b.0.cmp(&a.0));
    let selected = scores
        .into_iter()
        .take(k)
        .map(|(_, n)| n.clone())
        .collect();

    Ok(selected)
}
