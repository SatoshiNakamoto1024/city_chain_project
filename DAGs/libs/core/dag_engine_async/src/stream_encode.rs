// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\stream_encode.rs
//! 背景タスク: AsyncRead → QC-LDPC エンコード → ShardPacket mpsc 送信

use std::{io, sync::Arc};
use bytes::Bytes;
use tokio::{
    io::AsyncReadExt,
    sync::mpsc,
};
use crc32c::crc32c;

use crate::{ShardPacket, Tier, PipelineResult};
use ldpc::{
    encoder::LDPCEncoder,
    tiers::{CITY, CONTINENT, GLOBAL},
};

/// 一度に読むサイズ
const CHUNK: usize = 256 * 1024;

/// Tier に応じて (k, m) を返す
fn tier_params(tier: Tier) -> (usize, usize) {
    match tier {
        Tier::City      => (CITY.data_shards, CITY.parity_shards),
        Tier::Continent => (CONTINENT.data_shards, CONTINENT.parity_shards),
        Tier::Global    => (GLOBAL.data_shards, GLOBAL.parity_shards),
    }
}

/// 非同期タスク本体
pub async fn encode_task<R>(
    mut reader: R,
    enc: LDPCEncoder,
    tier: Tier,
    tx: mpsc::Sender<ShardPacket>,
) -> PipelineResult<()>
where
    R: tokio::io::AsyncRead + Unpin,
{
    let mut seq = 0u64;
    // LDPCEncoder は Clone できるよう Arc 包装しておく
    let enc = Arc::new(enc);
    let (k, m) = tier_params(tier);

    loop {
        // ① CHUNK バイト読む
        let mut buf = vec![0u8; CHUNK];
        let n = reader.read(&mut buf).await?;
        if n == 0 {
            // EOF
            break;
        }
        buf.truncate(n);

        // ② Blocking タスクでエンコード
        let enc_clone = enc.clone();
        // spawn_blocking のクロージャ内では std::io::Error とは別なので後で map_err
        let shards: Vec<Vec<u8>> = tokio::task::spawn_blocking(move || {
            // encode() のエラーは ECError なので `?` できないが
            // spawn_blocking の戻り値が Result<_,JoinError>
            // 外側で `??` を使うためここでは二重 Result
            enc_clone.encode(&buf, k, m)
        })
        .await
        .map_err(|e| io::Error::new(io::ErrorKind::Other, e))??;

        // ③ 各シャードを mpsc で送信
        let total = shards.len() as u32;
        for (idx, shard) in shards.into_iter().enumerate() {
            let pkt = ShardPacket {
                seq,
                idx: idx as u32,
                total,
                tier,
                crc32c: crc32c(&shard),
                payload: Bytes::from(shard),
            };
            tx.send(pkt)
                .await
                .map_err(|_| io::Error::new(io::ErrorKind::BrokenPipe, "channel closed"))?;
        }

        seq += 1;
    }

    Ok(())
}
