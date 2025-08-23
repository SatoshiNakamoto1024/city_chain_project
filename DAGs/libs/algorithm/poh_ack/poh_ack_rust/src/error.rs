// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\src\error.rs
// src/error.rs

//! ACK（Acknowledge）検証・管理モジュールで発生しうるエラー群を定義します。
//!
//! - Base58 デコード時のエラー
//! - Ed25519 公開鍵・署名バイト長エラー
//! - 署名／公開鍵フォーマットエラー
//! - 署名検証失敗エラー
//! - TTL(有効期限)超過エラー
//! - 重複 ID エラー
//! - IO／シリアライズエラー
//! - その他内部エラー

use thiserror::Error;
use std::io;
use serde_json;

/// ACK 操作時に起こりうる各種エラー
#[derive(thiserror::Error, Debug)]
pub enum AckError {
    /// Base58 のデコードに失敗した場合
    #[error("Base58 decode failed: {0}")]
    DecodeBase58(String),

    #[error("invalid json: {0}")]
    InvalidJson(#[from] serde_json::Error),

    /// 公開鍵のバイト列長が想定と異なる場合
    #[error("Invalid public key length: expected 32 bytes, got {0}")]
    InvalidKeyLength(usize),

    /// 署名のバイト列長が想定と異なる場合
    #[error("Invalid signature length: expected 64 bytes, got {0}")]
    InvalidSignatureLength(usize),

    /// 署名バイト列の構造自体が不正だった場合
    #[error("Invalid signature format: {0}")]
    InvalidSignature(String),

    /// 公開鍵バイト列の構造自体が不正だった場合
    #[error("Invalid public key format: {0}")]
    InvalidPublicKey(String),

    /// 署名検証に失敗した場合
    #[error("Signature verification failed: {0}")]
    SignatureVerification(String),

    /// TTL（有効期限）を超過していた場合
    #[error("TTL expired at {0}")]
    TtlExpired(String),

    /// 同一の ID を持つ ACK がすでに登録済みだった場合
    #[error("Duplicate id: {0}")]
    DuplicateId(String),

    /// ファイル IO（読み書き）でエラーが発生した場合
    #[error("IO error: {0}")]
    Io(String),

    /// ランタイム内部で予期しないエラーが発生した場合
    #[error("Internal error: {0}")]
    InternalError(String),
}

// -----------------------------------------------------------------------------
// 標準的なエラー型から AckError への変換を自動で行えるようにします。
// -----------------------------------------------------------------------------

/// `std::io::Error` → `AckError::Io`
impl From<io::Error> for AckError {
    fn from(err: io::Error) -> Self {
        AckError::Io(err.to_string())
    }
}
