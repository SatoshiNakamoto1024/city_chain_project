// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\sender\mod.rs
//! ネットワーク送信バックエンドの統括 (QUIC or TCP)
use crate::{ShardPacket, PipelineResult};

pub mod quic;
pub mod tcp;

/// *QUIC が使えれば優先*、失敗したら TCP フォールバック。
pub async fn send_packets(
    dst_addr: &str,
    mut rx: tokio::sync::mpsc::Receiver<ShardPacket>,
) -> PipelineResult<()> {
    match quic::send_quic(dst_addr, &mut rx).await {
        Ok(()) => Ok(()),
        Err(e) => {
            eprintln!("[sender] QUIC failed: {e:?} → fallback TCP");
            tcp::send_tcp(dst_addr, &mut rx).await
        }
    }
}
