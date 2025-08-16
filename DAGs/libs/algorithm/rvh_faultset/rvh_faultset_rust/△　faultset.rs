// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\src\faultset.rs

use crate::error::FaultsetError;

/// Perform latency-based failover selection.
///
/// # Arguments
///
/// * `nodes`      - List of node identifiers.
/// * `latencies`  - Parallel list of latencies (ms).
/// * `threshold`  - Maximum acceptable latency (ms).
///
/// # Returns
///
/// A Vec of node IDs whose latency ≤ threshold, sorted by ascending latency.
///
/// # Errors
///
/// Returns `FaultsetError` if inputs are invalid.
pub fn failover(
    nodes: &[String],
    latencies: &[f64],
    threshold: f64,
) -> Result<Vec<String>, FaultsetError> {
    if nodes.is_empty() {
        return Err(FaultsetError::EmptyNodes);
    }
    if nodes.len() != latencies.len() {
        return Err(FaultsetError::LengthMismatch(nodes.len(), latencies.len()));
    }
    if threshold < 0.0 {
        return Err(FaultsetError::NegativeThreshold(threshold));
    }

    // Pair up and filter
    let mut pairs: Vec<(&String, &f64)> = nodes.iter().zip(latencies.iter()).collect();
    pairs.retain(|&(_, &lat)| lat <= threshold);

    // Sort by latency ascending
    pairs.sort_by(|a, b| a.1.partial_cmp(b.1).unwrap_or(std::cmp::Ordering::Equal));

    Ok(pairs.into_iter().map(|(n, _)| n.clone()).collect())
}
