// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\receiver\quic.rs
//! QUIC 受信 (quinn)
//! ストリームを accept ⇒ そのまま MsgPack で `ShardPacket` 復元

use std::sync::Arc;
use quinn::{Endpoint, ServerConfig};
use tokio::{io::AsyncReadExt, sync::mpsc};
use crate::{ShardPacket, PipelineResult};

pub async fn listen_quic(bind: &str, tx: mpsc::Sender<ShardPacket>) -> PipelineResult<()> {
    let addr: std::net::SocketAddr = bind.parse().unwrap();

    // --- “自己署名 OK” なデモ証明書 ---
    let cert = rcgen::generate_simple_self_signed(vec!["ldpc.local".into()])
        .expect("rcgen");
    let key   = quinn::PrivateKey::from_der(&cert.serialize_private_key_der())?;
    let cert  = quinn::Certificate::from_der(&cert.serialize_der()?);

    let mut server_cfg = quinn::ServerConfig::with_single_cert(vec![cert], key)?;
    Arc::get_mut(&mut server_cfg.transport)
        .unwrap()
        .max_concurrent_uni_streams(1024_u32.into());

    let (endpoint, mut incoming) = Endpoint::server(server_cfg, addr)?;
    println!("[receiver] QUIC listening on {addr}");

    // accept-loop
    while let Some(conn) = incoming.next().await {
        let tx = tx.clone();
        tokio::spawn(async move {
            let quinn::NewConnection { mut uni_streams, .. } = conn.await.unwrap();
            while let Some(Ok(mut stream)) = uni_streams.next().await {
                let mut buf = Vec::new();
                stream.read_to_end(4 * 1024 * 1024, &mut buf).await.ok()?;
                if let Ok(pkt) = rmp_serde::from_slice::<ShardPacket>(&buf) {
                    let _ = tx.send(pkt).await;
                }
            }
        });
    }
    drop(endpoint);
    Ok(())
}
