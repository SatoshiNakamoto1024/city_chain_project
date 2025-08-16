// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\src\ttl.rs
use chrono::{DateTime, Duration, Utc};

use crate::error::AckError;

/// Ensure `ts` is not older than now − ttl_seconds
pub fn validate_ttl(ts: &DateTime<Utc>, ttl_seconds: i64) -> Result<(), AckError> {
    let now = Utc::now();
    if *ts + Duration::seconds(ttl_seconds) < now {
        Err(AckError::TtlExpired(ts.to_rfc3339()))
    } else {
        Ok(())
    }
}
