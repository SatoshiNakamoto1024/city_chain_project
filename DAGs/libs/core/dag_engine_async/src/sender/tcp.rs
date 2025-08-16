// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\sender\tcp.rs
//! シンプルな TCP フォールバック (TLS なし / デモ用途)

use std::io;
use tokio::{
    io::AsyncWriteExt,
    net::TcpStream,
    sync::mpsc::Receiver,
};
use crate::{ShardPacket, PipelineResult};

pub async fn send_tcp(addr: &str, rx: &mut Receiver<ShardPacket>) -> PipelineResult<()> {
    let mut stream = TcpStream::connect(addr).await?;
    while let Some(pkt) = rx.recv().await {
        let buf = rmp_serde::to_vec_named(&pkt).unwrap();
        // 書式: length-prefix (u32 LE) + msgpack
        stream.write_u32_le(buf.len() as u32).await?;
        stream.write_all(&buf).await?;
    }
    Ok(())
}
