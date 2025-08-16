// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\src\trace.rs

use once_cell::sync::OnceCell;
use opentelemetry::{global, KeyValue};
use opentelemetry_sdk::{
    metrics::controllers::push::PushController,     // PushController はここから
    Resource,
};
use tracing::{span, Level, Span};
use tracing_subscriber::{fmt, layer::SubscriberExt, EnvFilter, Registry};
use crate::error::TraceError;

/// Initialize global tracing + OTLP exporter. Idempotent.
pub fn init_tracing(filter: &str) -> Result<(), TraceError> {
    static ONCE: OnceCell<()> = OnceCell::new();
    ONCE.get_or_try_init(|| {
        // stdout formatting layer
        let fmt_layer = fmt::layer()
            .with_target(false)
            .with_level(true);

        // OTLP exporter tracer
        let tracer = opentelemetry_otlp::new_pipeline()
            .metrics(|metrics| metrics.with_resource(Resource::default()))
            .with_exporter(opentelemetry_otlp::ExportConfig::default())
            .install_simple()
            .map_err(|e| TraceError::Init(format!("OTLP init error: {}", e)))?;

        let otlp_layer = tracing_opentelemetry::layer().with_tracer(tracer);

        Registry::default()
            .with(EnvFilter::new(filter))
            .with(fmt_layer)
            .with(otlp_layer)
            .try_init()
            .map_err(|e| TraceError::Init(format!("tracing init error: {}", e)))
    })?;
    Ok(())
}

/// Create an INFO-level span with given name.
pub fn new_trace(name: &str) {
    let span = span!(Level::INFO, name);
}

/// Run a closure inside a named span and record key/value fields.
pub fn in_span<F, R>(name: &str, fields: &[(&str, &dyn std::fmt::Debug)], f: F) -> R
where
    F: FnOnce() -> R,
{
    let s = span!(Level::INFO, name);
    let _enter = s.enter();
    for (k, v) in fields {
        tracing::info!(%k, ?v);
    }
    f()
}

/// Macro for quick span creation with fields:
/// `record_span!("op", user = 42);`
#[macro_export]
macro_rules! record_span {
    ($name:expr $(, $k:ident = $v:expr)*) => {{
        let span = tracing::span!(tracing::Level::INFO, $name $(, $k = $v)*);
        let _enter = span.enter();
        span
    }};
}
