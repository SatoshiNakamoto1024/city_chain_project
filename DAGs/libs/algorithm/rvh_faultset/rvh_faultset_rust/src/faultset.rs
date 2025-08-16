// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\src\faultset.rs
use crate::error::FaultsetError;

/// Perform latency-based failover selection (sync).
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

    let mut pairs: Vec<(&String, &f64)> = nodes.iter().zip(latencies.iter()).collect();
    pairs.retain(|&(_, &lat)| lat <= threshold);
    pairs.sort_by(|a, b| a.1.partial_cmp(b.1).unwrap());
    Ok(pairs.into_iter().map(|(n, _)| n.clone()).collect())
}

/// Asynchronous version: spawn_blocking + Tokio.
pub async fn failover_async(
    nodes: Vec<String>,
    latencies: Vec<f64>,
    threshold: f64,
) -> Result<Vec<String>, FaultsetError> {
    tokio::task::spawn_blocking(move || failover(&nodes, &latencies, threshold))
        .await
        .expect("spawn_blocking panicked")
}
