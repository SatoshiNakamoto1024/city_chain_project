// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\grpc.rs
//! gRPC façade for PoH‑Hold‑Metrics
//!
//! * 双方向ストリーム Broadcast ― 高スループット登録
//! * 単発 Record            ― 単体テスト／簡易クライアント
//! * サーバストリーム Stats ― 現在の集計スナップショット
//!
//! **proto は変更せず** Rust 側のみで `tonic::async_trait` を満たすよう実装する。

use std::{net::ToSocketAddrs, pin::Pin, sync::Arc};

use async_stream::try_stream;
use prost_types::Timestamp;
use tokio_stream::{Stream, StreamExt};
use tonic::{transport::Server, Request, Response, Status};
use tonic_health::server::health_reporter;
use tonic_reflection::server::Builder as ReflectionBuilder;

use crate::{error::*, holdset::HoldAggregator, model::HoldEvent};
use crate::pb::{
    self,
    hold_metrics_server::{HoldMetrics, HoldMetricsServer},
    HoldAck, HoldMsg, HoldStat,
};

/// Stream 型エイリアス
type AckStream  = Pin<Box<dyn Stream<Item = Result<HoldAck , Status>> + Send>>;
type StatStream = Pin<Box<dyn Stream<Item = Result<HoldStat, Status>> + Send>>;

/// gRPC service スタブ
#[derive(Clone)]
pub struct GrpcSvc {
    agg: Arc<HoldAggregator>,
}

impl GrpcSvc {
    pub fn new(agg: Arc<HoldAggregator>) -> Self {
        Self { agg }
    }
}

#[tonic::async_trait]
impl HoldMetrics for GrpcSvc {
    type BroadcastStream = AckStream;
    type StatsStream     = StatStream;

    // ────────────────────────── ① Record (unary) ──────────────────────────
    async fn record(
        &self,
        request: Request<HoldMsg>,
    ) -> Result<Response<HoldAck>, Status> {
        let msg = request.into_inner();

        // HoldMsg → HoldEvent 変換
        let ev = HoldEvent {
            token_id:  msg.token_id,
            holder_id: msg.holder_id,
            start:     from_ts(msg.start)
                .map_err(|e| Status::invalid_argument(e.to_string()))?,
            end:       msg.end.map(|t| from_ts(Some(t)).unwrap()),
            weight:    msg.weight,
        };

        // 登録
        self.agg
            .record(&ev)
            .map_err(|e| Status::internal(e.to_string()))?;

        Ok(Response::new(HoldAck { ok: true, error: "".into() }))
    }

    // ────────────────────────── ② Broadcast (bidi‑stream) ─────────────────
    async fn broadcast(
        &self,
        request: Request<tonic::Streaming<HoldMsg>>,
    ) -> Result<Response<Self::BroadcastStream>, Status> {
        let mut in_stream = request.into_inner();
        let agg = self.agg.clone();

        let out_stream = try_stream! {
            while let Some(msg) = in_stream.next().await {
                let msg = msg?;
                let ev = HoldEvent {
                    token_id:  msg.token_id,
                    holder_id: msg.holder_id,
                    start:     from_ts(msg.start)
                        .map_err(|e| Status::invalid_argument(e.to_string()))?,
                    end:       msg.end.map(|t| from_ts(Some(t)).unwrap()),
                    weight:    msg.weight,
                };
                if let Err(e) = agg.record(&ev) {
                    yield Err(Status::internal(e.to_string()))?;
                }
                yield HoldAck { ok: true, error: "".into() };
            }
        };

        Ok(Response::new(Box::pin(out_stream) as AckStream))
    }

    // ────────────────────────── ③ Stats (server‑stream) ───────────────────
    async fn stats(
        &self,
        _request: Request<()>,
    ) -> Result<Response<Self::StatsStream>, Status> {
        // 現在の集計を 1 回だけ流す簡易実装
        let snapshot = self.agg.snapshot(); // Vec<model::HoldStat>

        let stream = tokio_stream::iter(snapshot.into_iter().map(|s| {
            Ok(HoldStat {
                holder_id:      s.holder_id,
                total_seconds:  s.total_seconds as i64,
                weighted_score: s.weighted_score,
                updated_at: Some(Timestamp {
                    seconds: s.updated_at.timestamp(),
                    nanos:   s.updated_at.timestamp_subsec_nanos() as i32,
                }),
            })
        }));

        Ok(Response::new(Box::pin(stream) as StatStream))
    }
}

/// Timestamp 変換ヘルパ
fn from_ts(ts: Option<Timestamp>) -> Result<chrono::DateTime<chrono::Utc>, HoldMetricsError> {
    ts.ok_or(HoldMetricsError::InvalidField).and_then(|t| {
        chrono::DateTime::from_timestamp(t.seconds, t.nanos as _)
            .ok_or(HoldMetricsError::InvalidField)
    })
}

/// gRPC サーバー起動エントリ
///
/// ```ignore
/// let agg = Arc::new(HoldAggregator::default());
/// serve("0.0.0.0:50051", agg).await.unwrap();
/// ```
pub async fn serve<A: ToSocketAddrs>(
    addr: A,
    agg: Arc<HoldAggregator>,
) -> Result<(), Box<dyn std::error::Error>> {
    // health / reflection
    let (mut reporter, health_svc) = health_reporter();
    reporter.set_serving::<HoldMetricsServer<GrpcSvc>>().await;

    let reflection = ReflectionBuilder::configure()
        .register_encoded_file_descriptor_set(pb::FILE_DESCRIPTOR_SET)
        .build_v1()?; // v1, v1alpha どちらでも可

    Server::builder()
        .add_service(health_svc)
        .add_service(reflection)
        .add_service(HoldMetricsServer::new(GrpcSvc::new(agg)))
        .serve(addr.to_socket_addrs()?.next().unwrap())
        .await?;

    Ok(())
}
