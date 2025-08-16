// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\tests\test_pipeline.rs
//! Tokio で実際に sender ↔ receiver ↔ decoder まで繋げる統合テスト
#![cfg(all(feature = "runtime-tokio", feature = "quic"))]

use tokio::sync::mpsc;
use ldpc::{
    encoder::LDPCEncoder,
    decoder::peeling::PeelingDecoder,
    encode_stream, decode_stream,
    receiver::spawn_listener, 
    sender::send_packets, 
    tiers::{CITY_CFG, CITY_H},
};

#[tokio::test(flavor = "multi_thread")]
async fn e2e_pipeline_city() {
    let bind = "127.0.0.1:4600";

    // ---------------- Net listener (receiver side) -------------
    let (pkt_tx, pkt_rx) = mpsc::channel(128);
    tokio::spawn(spawn_listener(bind, pkt_tx));

    // ---------------- Decoder pipe ------------------------------
    let dec = PeelingDecoder::new(CITY_H.clone(), CITY_CFG.data_shards);
    let mut out = Vec::new();
    let out_sink = tokio::io::sink(); // discard → ensure no panic

    decode_stream(pkt_rx, dec, out_sink);

    // ---------------- Encode + Send side ------------------------
    let data = vec![0u8; 5 * 1024 * 1024]; // 5 MiB dummy
    let (mut read_rd, mut write_rd) = tokio::io::duplex(64 * 1024);
    tokio::spawn(async move { write_rd.write_all(&data).await.unwrap() });

    let encoder = LDPCEncoder::new(CITY_CFG, 0xC17E);
    let (tx, rx) = mpsc::channel(128);
    encode_stream(&mut read_rd, encoder, Tier::City, tx);
    tokio::spawn(send_packets(bind, rx));

    // wait until everything flushed
    tokio::time::sleep(std::time::Duration::from_secs(5)).await;
}
