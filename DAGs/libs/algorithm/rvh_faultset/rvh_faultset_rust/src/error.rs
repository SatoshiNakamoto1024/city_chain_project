// D:\city_chain_project\DAGs\libs\algorithm\rvh_faultset\rvh_faultset_rust\src\error.rs
use thiserror::Error;

/// Errors for the faultset algorithm.
#[derive(Debug, Error, PartialEq)]
pub enum FaultsetError {
    /// Provided node list is empty.
    #[error("node list is empty")]
    EmptyNodes,
    /// Node count and latency list length mismatch.
    #[error("nodes length ({0}) != latencies length ({1})")]
    LengthMismatch(usize, usize),
    /// Threshold is negative.
    #[error("threshold must be non-negative, got {0}")]
    NegativeThreshold(f64),
}
