// D:\city_chain_project\DAGs\libs\algorithm\rvh_trace\rvh_trace_rust\src\main_trace.rs
//! CLI サンプル

use tracing::info;
use rvh_trace_rust::{init_tracing, new_span};

/// Tokio runtime を張るだけで OK
#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_tracing("info")?;             // ← ここでもう panic しない
    let span = new_span("demo_cli");
    let _enter = span.enter();
    info!("hello from CLI");
    Ok(())
}
