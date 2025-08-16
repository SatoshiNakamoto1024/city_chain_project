// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\lib.rs
//! ldpc-pipeline – 非同期ストリーミング Erasure Coding & 送受信
//! ===============================================================
//! ```no_run
//! use ldpc_pipeline::{encode_stream, send};
//! # tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap().block_on(async {
//! let (mut tx, finished) = encode_stream(b"example data", 8, 4).await?;
//! send::tcp::send_stream("127.0.0.1:4000", &mut tx).await?;
//! finished.await?;            // 全シャード送信完了を待つ
//! # Ok::<(), ldpc_pipeline::PipelineError>(())
//! # });
//! ```
//!
//! * **stream_encode / stream_decode** ─ シャード化・復元
//! * **sender / receiver**            ─ TCP あるいは QUIC ネットワーク I/O
//! * **util**                         ─ CRC32C / BLAKE3 / バッファプール
//!
//! Cargo feature
//! -------------
//! * `default = ["tcp", "quic"]` → TCP+QUIC 両対応
//! * `--no-default-features --features tcp` のように片方だけ有効化も可能

#![warn(missing_docs)]

/* ---------- 公開エラ―型 -------------------------------------------------- */

use thiserror::Error;

/// パイプライン全体で使う高レベルエラー
#[derive(Debug, Error)]
pub enum PipelineError {
    /// プロトコル・シリアライズ系
    #[error("protocol error: {0}")]
    Proto(String),

    /// ネットワーク下位 I/O
    #[error("network error: {0}")]
    Io(#[from] std::io::Error),

    /// QUIC ラッパ
    #[cfg(feature = "quic")]
    #[error("quic error: {0}")]
    Quic(#[from] quinn::WriteError),

    /// 内部チャネルやタスク join
    #[error("task join error: {0}")]
    Join(#[from] tokio::task::JoinError),

    /// エンコード / デコード失敗
    #[error("codec error: {0}")]
    Codec(#[from] ldpc::ECError),
}

/* ---------- 下位モジュール ------------------------------------------------ */

pub mod util;

pub mod stream_encode;
pub mod stream_decode;

pub mod sender;
pub mod receiver;

/* ---------- 主要 re-export ------------------------------------------------ */

pub use crate::stream_encode::{encode_stream, ShardStream, EncodeConfig};
pub use crate::stream_decode::{decode_stream, DecodeConfig};

/// ネット送信 (`sender::*`) / 受信 (`receiver::*`) のまとめ re-export
pub mod send {
    #[cfg(feature = "tcp")]
    pub use crate::sender::tcp::*;
    #[cfg(feature = "quic")]
    pub use crate::sender::quic::*;
}
pub mod recv {
    #[cfg(feature = "tcp")]
    pub use crate::receiver::tcp::*;
    #[cfg(feature = "quic")]
    pub use crate::receiver::quic::*;
}

/* ---------- 初期化ヘルパ -------------------------------------------------- */

use once_cell::sync::Lazy;
use tracing_subscriber::{fmt, EnvFilter};

/// 初回呼び出し時に `tracing_subscriber` をセットアップするだけのヘルパ。
static _INIT_TRACING: Lazy<()> = Lazy::new(|| {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,ldpc_pipeline=debug"));
    fmt().with_env_filter(filter).init();
});

/// ライブラリを最初に使う前に呼ぶと、きれいにログが出る。
pub fn init_tracing() {
    let _ = *_INIT_TRACING; // 実行するだけ
}
