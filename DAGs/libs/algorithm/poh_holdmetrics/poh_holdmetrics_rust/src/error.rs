// \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\errors.rs
use thiserror::Error;

#[derive(Debug, Error)]
pub enum HoldMetricsError {
    #[error("token_id / holder_id must be non-empty")]
    InvalidField,
    #[error("start timestamp occurs after end timestamp")]
    InvalidDuration,
    #[error("storage error: {0}")]
    Storage(String),
    #[error("internal: {0}")]
    Internal(String),
}

pub type Result<T, E = HoldMetricsError> = std::result::Result<T, E>;
