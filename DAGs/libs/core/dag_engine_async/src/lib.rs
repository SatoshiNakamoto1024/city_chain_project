// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\lib.rs
//! 非同期 QC-LDPC パイプライン
//! ```rust
//! use ldpc_pipeline::{encode_stream, decode_stream, ShardPacket, Tier};
//! ```
#[cfg(feature = "stub-core")]
mod core_stub;
#[cfg(feature = "stub-core")]
pub use core_stub as ldpc_core;   // ← クレート内で “ldpc_core::…” と書ける

// 将来、本物を使う時は ↓ だけ変えれば済む
// #[cfg(not(feature = "stub-core"))]
// extern crate ldpc_core as ldpc_core;

use std::io;
use bytes::Bytes;
use serde::{Deserialize, Serialize};
use tokio::io::{AsyncRead, AsyncWrite};
use tokio::sync::mpsc;

use ldpc::encoder::LDPCEncoder;
use ldpc::decoder::peeling::PeelingDecoder;
use ldpc::ErasureCoder;

// --- 下層モジュール -------------------------------------------------

pub use stream_encode::encode_task as encode_stream;
pub use stream_decode::decode_task as decode_stream;
pub use crate::stream_encode::{ShardPacket, Tier, PipelineResult};

pub mod sender;
pub mod receiver;
pub mod util;

// --- 型定義 --------------------------------------------------------

/// どのティア行列で符号化されたパケットか
#[repr(u8)]
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum Tier {
    City      = 0,
    Continent = 1,
    Global    = 2,
}

/// ネットワークを流れる 1 パケット
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShardPacket {
    pub seq:     u64,    // 通番
    pub idx:     u32,    // シャード番号
    pub total:   u32,    // k + m
    pub tier:    Tier,
    pub payload: Bytes,  // 圧縮可
    pub crc32c:  u32,    // 0 なら無検証
}

/// Result エイリアス
pub type PipelineResult<T> = Result<T, io::Error>;

// ================ エンコード ================ //

/// 読み込んだストリームを LDPC シャーディングし
/// `ShardPacket` として非同期送信するタスクを spawn する。
pub fn encode_stream<R>(
    reader: R,
    enc: LDPCEncoder,
    tier: Tier,
    tx: mpsc::Sender<ShardPacket>,
) -> tokio::task::JoinHandle<PipelineResult<()>>
where
    R: AsyncRead + Send + Unpin + 'static,
{
    tokio::spawn(stream_encode::encode_task(reader, enc, tier, tx))
}

// ================ デコード ================ //

/// 受信した `ShardPacket` から復元し `out` に書き出すタスクを spawn。
pub fn decode_stream<W, D>(
    rx: mpsc::Receiver<ShardPacket>,
    dec: D,
    out: W,
) -> tokio::task::JoinHandle<PipelineResult<()>>
where
    W: AsyncWrite + Send + Unpin + 'static,
    D: ErasureCoder + Send + Sync + 'static,
{
    tokio::spawn(stream_decode::decode_task(rx, dec, out))
}
