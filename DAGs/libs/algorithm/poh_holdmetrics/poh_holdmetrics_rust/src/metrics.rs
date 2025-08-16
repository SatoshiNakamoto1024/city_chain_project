// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\metrics.rs
//! Prometheus gauge / counter initialisation.
use once_cell::sync::Lazy;
use prometheus::{opts, register_counter, register_histogram, Counter, Histogram};

pub static HOLD_EVENTS: Lazy<Counter> =
    Lazy::new(|| register_counter!(opts!("hold_events_total", "Total HoldEvents processed")).unwrap());

pub static HOLD_SCORE_HISTO: Lazy<Histogram> = Lazy::new(|| {
    register_histogram!(
        "hold_score_seconds",
        "Histogram of hold seconds * weight",
        vec![1.0, 10.0, 60.0, 600.0, 3600.0, 86400.0]
    )
    .unwrap()
});
