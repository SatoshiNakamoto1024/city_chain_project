// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\sender\quic.rs
//! QUIC 送信 (quinn)
//! - 各シャード seq ごとに独立ストリームを張り直す
//! - datagram モードでも良いが、ここでは reliable-stream

use std::net::ToSocketAddrs;
use bytes::Bytes;
use futures::{StreamExt};
use quinn::{ClientConfig, Connection, Endpoint};
use tokio::sync::mpsc::Receiver;

use crate::{ShardPacket, PipelineResult};

async fn connect(addr: &str) -> PipelineResult<Connection> {
    let mut endpoints = addr.to_socket_addrs()?;
    let sock_addr = endpoints
        .next()
        .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidInput, "invalid addr"))?;

    // Insecure demo config (self-signed)
    let mut cfg = ClientConfig::with_native_roots();
    cfg.crypto
        .dangerous()
        .set_certificate_verifier(std::sync::Arc::new(quinn::crypto::rustls::webpki_roots::NoCertificateVerification {}));
    let endpoint = Endpoint::client("[::]:0".parse().unwrap())?;
    let conn = endpoint.connect_with(cfg, sock_addr, "ldpc")?.await?;
    Ok(conn)
}

/// Main sending loop
pub async fn send_quic(addr: &str, rx: &mut Receiver<ShardPacket>) -> PipelineResult<()> {
    let conn = connect(addr).await?;
    while let Some(pkt) = rx.recv().await {
        let mut stream = conn.open_uni().await?;
        let buf = rmp_serde::to_vec_named(&pkt).unwrap();
        stream.write_all(&buf).await?;
        stream.finish().await?;
    }
    Ok(())
}
