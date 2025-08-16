// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\receiver\tcp.rs
//! TCP 受信フォールバック (length-prefix + MsgPack)

use tokio::{
    io::{AsyncReadExt},
    net::TcpListener,
    sync::mpsc,
};
use crate::{ShardPacket, PipelineResult};

pub async fn listen_tcp(bind: &str, tx: mpsc::Sender<ShardPacket>) -> PipelineResult<()> {
    let listener = TcpListener::bind(bind).await?;
    println!("[receiver] TCP listening on {bind}");

    loop {
        let (mut sock, _) = listener.accept().await?;
        let tx_clone = tx.clone();

        tokio::spawn(async move {
            loop {
                let len = match sock.read_u32_le().await {
                    Ok(l) => l as usize,
                    Err(_) => break,
                };
                let mut buf = vec![0u8; len];
                if sock.read_exact(&mut buf).await.is_err() {
                    break;
                }
                if let Ok(pkt) = rmp_serde::from_slice::<ShardPacket>(&buf) {
                    let _ = tx_clone.send(pkt).await;
                }
            }
        });
    }
}
