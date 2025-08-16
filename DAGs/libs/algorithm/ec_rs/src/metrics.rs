// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\metrics.rs
//! Metrics collection for EC encode/decode operations.
//!
//! Cumulative timers are stored in atomics and can be queried at runtime
//! to track total CPU time spent in each phase.

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

/// Total nanoseconds spent in `encode` calls.
static ENCODE_TIME_NS: AtomicU64 = AtomicU64::new(0);
/// Total nanoseconds spent in `decode` calls.
static DECODE_TIME_NS: AtomicU64 = AtomicU64::new(0);

/// Record the duration of an operation.
///
/// # Arguments
///
/// * `op`  – either `"encode"` or `"decode"`
/// * `dur` – wall‐clock duration of that operation
pub fn record(op: &str, dur: Duration) {
    let ns = dur.as_nanos() as u64;
    match op {
        "encode" => { ENCODE_TIME_NS.fetch_add(ns, Ordering::Relaxed); }
        "decode" => { DECODE_TIME_NS.fetch_add(ns, Ordering::Relaxed); }
        _ => { /* ignore unknown */ }
    }
}

/// Returns the total time in nanoseconds spent in all `encode` calls.
pub fn get_encode_time() -> u64 {
    ENCODE_TIME_NS.load(Ordering::Relaxed)
}

/// Returns the total time in nanoseconds spent in all `decode` calls.
pub fn get_decode_time() -> u64 {
    DECODE_TIME_NS.load(Ordering::Relaxed)
}
