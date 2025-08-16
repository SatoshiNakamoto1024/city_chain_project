// \city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\tests\test_grpc.rs
#![cfg(feature = "grpc")]   // ← gRPC ビルド時だけコンパイル

use std::net::TcpListener;
use std::sync::Arc;
use std::time::Duration as StdDur;

use chrono::{Duration, Utc};
use poh_holdmetrics_rust::{grpc, holdset::HoldAggregator, pb};
use prost_types::Timestamp;
use tokio::time::{sleep, timeout, Instant};
use tokio_stream::wrappers::ReceiverStream;
use tokio_stream::StreamExt;
use tonic::transport::{Channel, Endpoint};

/// 接続リトライ（最大 `total` まで待つ）
async fn connect_with_retry(url: &str, total: StdDur) -> anyhow::Result<Channel> {
    let deadline = Instant::now() + total;
    loop {
        match Endpoint::from_shared(url.to_string())?.connect().await {
            Ok(ch) => return Ok(ch),
            Err(e) if Instant::now() < deadline => {
                // サーバの accept ループが立ち上がるまで少し待って再試行
                sleep(StdDur::from_millis(50)).await;
                continue;
            }
            Err(e) => return Err(e.into()),
        }
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn grpc_broadcast_roundtrip() {
    // ── ① 空きポート確保（:0 で OS に割り当ててもらう） ─────────────
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let addr_str = addr.to_string(); // "127.0.0.1:12345"
    drop(listener); // 直ちに閉じる（このポートをサーバがすぐ bind する）

    // ── ② サーバ起動（非同期に動かす） ───────────────────────────
    let agg = Arc::new(HoldAggregator::default());
    let srv = tokio::spawn({
        let agg = Arc::clone(&agg);
        let addr_owned = addr_str.clone();
        async move {
            // あなたの実装: 指定アドレスで serve
            grpc::serve(&addr_owned, agg).await.unwrap();
        }
    });

    // 起動直後のレース回避に、軽く待つ（保険）
    sleep(StdDur::from_millis(50)).await;

    // ── ③ クライアント接続（最大 2 秒リトライ） ────────────────
    let endpoint = format!("http://{}", addr_str);
    let channel = connect_with_retry(&endpoint, StdDur::from_secs(2))
        .await
        .expect("connect_with_retry failed");
    let mut client = pb::hold_metrics_client::HoldMetricsClient::new(channel);

    // ── ④ 1 件だけ HoldMsg を送信 ────────────────────────────────
    let now = Utc::now();
    let msg = pb::HoldMsg {
        token_id: "TK".into(),
        holder_id: "HD".into(),
        start: Some(Timestamp {
            seconds: (now - Duration::seconds(3)).timestamp(),
            nanos: 0,
        }),
        end: Some(Timestamp {
            seconds: now.timestamp(),
            nanos: 0,
        }),
        weight: 1.0,
    };

    let (tx, rx) = tokio::sync::mpsc::channel(1);
    tx.send(msg).await.unwrap();
    drop(tx); // ストリーム終端

    let inbound = ReceiverStream::new(rx);
    let mut stream = client.broadcast(inbound).await.unwrap().into_inner();

    // ── ⑤ 5 秒以内に ACK を受信 ──────────────────────────────────
    let ack = timeout(StdDur::from_secs(5), stream.next())
        .await
        .expect("timeout while waiting ack")
        .expect("stream closed unexpectedly")
        .unwrap();
    assert!(ack.ok, "ACK.ok should be true");

    // サーバ停止（テスト用）
    srv.abort();
}
