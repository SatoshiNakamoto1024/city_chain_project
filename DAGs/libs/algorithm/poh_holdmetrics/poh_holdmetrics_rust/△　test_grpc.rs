// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\tests\test_grpc.rs
#![cfg(feature = "grpc")]   // ← gRPC ビルド時だけコンパイル

use std::{net::TcpListener, sync::Arc, time::Duration as StdDur};
use chrono::{Duration, Utc};
use poh_holdmetrics_rust::{grpc, holdset::HoldAggregator, pb};
use prost_types::Timestamp;
use tokio::time::timeout;

#[tokio::test(flavor = "multi_thread")]
async fn grpc_broadcast_roundtrip() {
    // ── ① 空きポート確保 ─────────────────────────────
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let addr_str = addr.to_string();                    // String → "127.0.0.1:12345"
    drop(listener);                                     // 直ちに閉じる

    // ── ② サーバ起動（addr_str は &str 参照で渡すだけ） ─────────
    let agg = Arc::new(HoldAggregator::default());
    let srv = tokio::spawn({
        let agg = Arc::clone(&agg);
        let addr_owned = addr_str.clone();              // ★clone して move する
        async move { grpc::serve(&addr_owned, agg).await.unwrap() }
    });

    // ── ③ クライアント接続 ─────────────────────────
    use tonic::transport::Endpoint;
    let channel = Endpoint::from_shared(format!("http://{}", addr_str))
        .unwrap()
        .connect()
        .await
        .unwrap();
    let mut client = pb::hold_metrics_client::HoldMetricsClient::new(channel);

    // ── ④ 1 件だけ HoldMsg を送信 ───────────────────
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
    drop(tx);                                           // ストリーム終端

    let inbound = tokio_stream::wrappers::ReceiverStream::new(rx);
    let mut stream = client.broadcast(inbound).await.unwrap().into_inner();

    // ── ⑤ 5 秒以内に ACK を受信 ──────────────────────
    use tokio_stream::StreamExt;                        // ここだけ必要
    let ack = timeout(StdDur::from_secs(5), stream.next())
        .await
        .expect("timeout")
        .expect("stream closed")
        .unwrap();
    assert!(ack.ok, "ACK.ok should be true");

    srv.abort();
}
