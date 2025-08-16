// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\src\trace.rs
// src/trace.rs
use once_cell::sync::OnceCell;
use tracing::{Level, Span};
use crate::error::TraceError;

// --- 先頭付近に追記／修正 ---------------------------------
static RUNTIME:  once_cell::sync::OnceCell<tokio::runtime::Runtime> = OnceCell::new();
static SUB_INIT: once_cell::sync::OnceCell<()>                      = OnceCell::new();
// -----------------------------------------------------------

// ─────────────────────────────────────────────────────────────
// 共通: レイヤ組み立て & tracing_subscriber 初期化
pub fn init_tracing(filter: &str) -> Result<(), TraceError> {
    // ── ここで必ず stderr に現在の状況を出す ───────────────
    eprintln!(
        "[rvh] init_tracing: Handle::try_current() = {:?}",
        tokio::runtime::Handle::try_current()
    );

    SUB_INIT.get_or_try_init(|| {
        // すでにランタイムならそのまま
        if tokio::runtime::Handle::try_current().is_ok() {
            setup_subscriber(filter)
        } else {
            // 自前ランタイムを作り、そのスレッドに入って実行
            let rt = tokio::runtime::Builder::new_current_thread()
                     .enable_all()
                     .build()
                     .map_err(|e| TraceError::Init(e.to_string()))?;
            let _guard = rt.enter();             // <- ここがポイント 
            let res = setup_subscriber(filter);
            RUNTIME.set(rt).ok();
            res
        }
    })?;
    Ok(())
}

// 共通ロジックは分離しておくとテストしやすい
fn setup_subscriber(filter: &str) -> Result<(), TraceError> {
    use tracing_subscriber::{fmt, layer::SubscriberExt, util::SubscriberInitExt, EnvFilter, Registry};

    let fmt_layer = fmt::layer().with_target(false).with_level(true);

    let exporter = opentelemetry_otlp::new_pipeline()
        .tracing()
        .with_exporter(opentelemetry_otlp::new_exporter().tonic())
        .install_simple()
        .map_err(|e| TraceError::Init(format!("OTLP init error: {}", e)))?;

    let otlp_layer = tracing_opentelemetry::layer().with_tracer(exporter);

    Registry::default()
        .with(EnvFilter::new(filter))
        .with(fmt_layer)
        .with(otlp_layer)
        .try_init()
        .map_err(|e| TraceError::Init(format!("tracing init error: {}", e)))
}

// ─────────────────────────────────────────────────────────────
// ユーティリティ
pub fn new_span(name: &str) -> Span {
    tracing::span!(Level::INFO, "span", name = %name)
}

pub fn in_span<F, R>(name: &str, fields: &[(&str, &dyn std::fmt::Debug)], f: F) -> R
where
    F: FnOnce() -> R,
{
    let span  = new_span(name);
    let _enter = span.enter();
    for (k, v) in fields {
        span.record(*k, &format!("{:?}", v));
    }
    f()
}

#[macro_export]
macro_rules! record_span {
    ($name:expr $(, $k:ident = $v:expr)*) => {{
        let span = tracing::span!(
            tracing::Level::INFO, "span", name = $name $(, $k = ?$v)*
        );
        let _enter = span.enter();
        span
    }};
}
