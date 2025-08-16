// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\src\error.rs

use thiserror::Error;

/// Errors possible during trace initialization or use.
#[derive(Debug, Error)]
pub enum TraceError {
    #[error("initialization failed: {0}")]
    Init(String),
}
