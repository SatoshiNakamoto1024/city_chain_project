// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\main_holdmetrics.rs
//! Stand-alone binary (gRPC server + Prometheus exporter)

use std::sync::Arc;

use hyper::{
    service::{make_service_fn, service_fn},
    Body, Response, Server,
};
use poh_holdmetrics_rust::{grpc, holdset::HoldAggregator};
use prometheus::{Encoder, TextEncoder};
use tokio::{signal, task};
use tracing_subscriber::{EnvFilter, FmtSubscriber};

#[tokio::main(flavor = "multi_thread", worker_threads = 4)]
async fn main() -> anyhow::Result<()> {
    // ── Structured JSON logging ──────────────────────────────
    FmtSubscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .json()
        .init();

    // ── Shared in-memory aggregator ──────────────────────────
    let agg = Arc::new(HoldAggregator::default());

    // ── gRPC server ──────────────────────────────────────────
    let grpc_handle = {
        let agg = Arc::clone(&agg);
        task::spawn(async move {
            grpc::serve("0.0.0.0:60051", agg)
                .await
                .expect("gRPC server failed");
        })
    };

    // ── Prometheus /metrics exporter ─────────────────────────
    let metrics_handle = task::spawn(async {
        let addr = ([0, 0, 0, 0], 9100).into();

        let make_svc = make_service_fn(|_| async {
            Ok::<_, hyper::Error>(service_fn(|_req| async {
                // TextEncoder は Clone 不可 → 都度生成
                let encoder = TextEncoder::new();
                let metric_families = prometheus::gather();
                let mut buf = Vec::with_capacity(8 * 1024);
                encoder.encode(&metric_families, &mut buf).unwrap();
                Ok::<_, hyper::Error>(Response::new(Body::from(buf)))
            }))
        });

        Server::bind(&addr)
            .serve(make_svc)
            .await
            .expect("HTTP metrics server failed");
    });

    tracing::info!("PoHold gRPC ▶ 0.0.0.0:60051");
    tracing::info!("Prometheus ▶ 0.0.0.0:9100/metrics");

    // ── Graceful shutdown on Ctrl-C ─────────────────────────
    signal::ctrl_c().await?;
    tracing::info!("Shutdown signal received");

    grpc_handle.abort();
    metrics_handle.abort();
    Ok(())
}
