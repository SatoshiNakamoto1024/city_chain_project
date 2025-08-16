// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\grpc.rs
//! gRPC server – PoHold Metrics broadcast

use std::{net::ToSocketAddrs, pin::Pin, sync::Arc};

use async_stream::try_stream;
use prost_types::Timestamp;
use tokio_stream::StreamExt;
use tonic::{
    transport::{Server, ServerTlsConfig},
    Request, Response, Status,
};
use tonic_health::server::health_reporter;
use tonic_reflection::server::Builder as ReflectionBuilder;

use crate::{error::*, holdset::HoldAggregator, model::HoldEvent};

use crate::pb::{
     self,
     hold_metrics_server::{HoldMetrics, HoldMetricsServer},
     HoldAck, HoldMsg,
 };

type AckStream = Pin<Box<dyn tokio_stream::Stream<Item = Result<HoldAck, Status>> + Send>>;

/// gRPC service struct
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

    async fn broadcast(
        &self,
        request: Request<tonic::Streaming<HoldMsg>>,
    ) -> Result<Response<Self::BroadcastStream>, Status> {
        let mut stream = request.into_inner();
        let agg = self.agg.clone();

        let outbound = try_stream! {
            while let Some(msg) = stream.next().await {
                let msg = msg?;
                // --- convert HoldMsg -> HoldEvent --------------------------
                let ev = HoldEvent {
                    token_id: msg.token_id,
                    holder_id: msg.holder_id,
                    start: from_ts(msg.start).map_err(|e| Status::invalid_argument(e.to_string()))?,
                    end: msg.end.map(|t| from_ts(Some(t)).unwrap()),
                    weight: msg.weight,
                };
                // --- record -------------------------------------------------
                if let Err(e) = agg.record(&ev) {
                    yield Err(Status::internal(e.to_string()))?;
                }
                // --- immediate ACK -----------------------------------------
                yield HoldAck { ok: true, error: "".into() };
            }
        };

        Ok(Response::new(Box::pin(outbound) as AckStream))
    }
}

/// Timestamp helper
fn from_ts(ts: Option<Timestamp>) -> Result<chrono::DateTime<chrono::Utc>, HoldMetricsError> {
    ts.ok_or(HoldMetricsError::InvalidField).and_then(|t| {
        chrono::DateTime::from_timestamp(t.seconds, t.nanos as _)
            .ok_or(HoldMetricsError::InvalidField)
    })
}

/// Public bootstrap entry – used by main_holdmetrics.rs & tests
pub async fn serve<A: ToSocketAddrs>(
    addr: A,
    agg: Arc<HoldAggregator>,
) -> Result<(), Box<dyn std::error::Error>> {
    // --- health & reflection --------------------------------------------
    let (mut reporter, health_service) = health_reporter();
    reporter.set_serving::<HoldMetricsServer<GrpcSvc>>().await;

    let reflection = ReflectionBuilder::configure()
        .register_encoded_file_descriptor_set(pb::FILE_DESCRIPTOR_SET)
        .build_v1()?;        // ★ここだけ変更

    Server::builder()
        // 平文で十分なら TLS 設定を外す。後日 `rustls_pemfile` + `identity` で追加可
        //".tls_config(ServerTlsConfig::new().rustls_client_disabled())?"

        .add_service(health_service)
        .add_service(reflection)
        .add_service(HoldMetricsServer::new(GrpcSvc::new(agg)))
        .serve(addr.to_socket_addrs()?.next().unwrap())
        .await?;

    Ok(())
}
