// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\stream_decode.rs
//! 背景タスク:  ShardPacket 受信 → 復元可能か判定 → 完成データを AsyncWrite
use std::io;
use bytes::Bytes;
use dashmap::DashMap;
use tokio::{
    io::AsyncWriteExt,
    sync::mpsc,
};
use crate::{ShardPacket, PipelineResult};
use ldpc_core::ErasureCoder;

/// (seq → Vec<Option<Bytes>>)
type ShardPool = DashMap<u64, Vec<Option<Bytes>>>;

pub async fn decode_task<W, D>(
    mut rx: mpsc::Receiver<ShardPacket>,
    dec: D,
    mut out: W,
) -> PipelineResult<()>
where
    W: tokio::io::AsyncWrite + Unpin,
    D: ErasureCoder,
{
    let pool: ShardPool = DashMap::new();

    while let Some(pkt) = rx.recv().await {
        let entry = pool
            .entry(pkt.seq)
            .or_insert_with(|| vec![None; pkt.total as usize]);
        entry[pkt.idx as usize] = Some(pkt.payload.clone());

        // 全シャード揃った？(or k 以上？ → peeling が対応)
        let present = entry.iter().filter(|s| s.is_some()).count();
        if present as u32 >= pkt.total {   // 過剰でも OK
            let shards_opt: Vec<_> = entry
                .iter()
                .map(|opt| opt.as_ref().map(|b| b.to_vec()))
                .collect();

            // 重い処理は blocking へ
            let dec_clone = dec.clone_box();
            let data = tokio::task::spawn_blocking(move || {
                dec_clone.decode(shards_opt, dec_clone.k(), dec_clone.m())
            })
            .await
            .map_err(|e| io::Error::new(io::ErrorKind::Other, e))??;

            out.write_all(&data).await?;
            pool.remove(&pkt.seq);      // メモリ解放
        }
    }
    out.flush().await?;
    Ok(())
}
