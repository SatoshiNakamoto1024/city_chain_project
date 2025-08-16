// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\receiver\mod.rs
//! 受信側: ネットワークから `ShardPacket` を取得し mpsc へ転送
//! ```rust
//! use ldpc::pipeline::receiver::spawn_listener;
//! ```

use tokio::sync::mpsc;
use crate::{ShardPacket, PipelineResult};

pub mod quic;
pub mod tcp;

/// QUIC を優先。利用不可なら TCP ソケットにフォールバック。
pub async fn spawn_listener(
    bind_addr: &str,
    tx: mpsc::Sender<ShardPacket>,
) -> PipelineResult<()> {
    match quic::listen_quic(bind_addr, tx.clone()).await {
        Ok(()) => Ok(()),
        Err(e) => {
            eprintln!("[receiver] QUIC listener failed: {e:?} → fallback TCP");
            tcp::listen_tcp(bind_addr, tx).await
        }
    }
}
