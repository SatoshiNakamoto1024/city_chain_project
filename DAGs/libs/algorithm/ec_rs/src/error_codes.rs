// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\error_codes.rs

use std::io;
use thiserror::Error;
use http::StatusCode;

/// Erasure‐Coding 全体で扱うエラー
#[derive(Debug, Error)]
pub enum ECError {
    /// 設定ファイルの読み込みや検証に失敗
    #[error("Configuration error: {0}")]
    Config(String),

    /// 符号化時のエラー
    #[error("Encoding error: {0}")]
    Encode(String),

    /// 復元時のエラー
    #[error("Decoding error: {0}")]
    Decode(String),

    /// I/O 周りの汎用エラー
    #[error("I/O error: {0}")]
    Io(#[from] io::Error),
}

/// 数値コードと HTTP ステータスのマッピング用列挙
#[derive(Debug, Clone, Copy)]
pub enum ECErrorCode {
    Configuration = 1001,
    Encoding      = 1002,
    Decoding      = 1003,
    Io            = 1004,
}

impl ECError {
    /// このエラーに対応する数値コードを返す
    pub fn code(&self) -> i32 {
        match self {
            ECError::Config(_) => ECErrorCode::Configuration as i32,
            ECError::Encode(_) => ECErrorCode::Encoding      as i32,
            ECError::Decode(_) => ECErrorCode::Decoding      as i32,
            ECError::Io(_)     => ECErrorCode::Io            as i32,
        }
    }

    /// このエラーに対応する HTTP ステータスを返す
    pub fn status(&self) -> StatusCode {
        match self {
            ECError::Config(_)       => StatusCode::BAD_REQUEST,
            ECError::Encode(_)       => StatusCode::INTERNAL_SERVER_ERROR,
            ECError::Decode(_)       => StatusCode::INTERNAL_SERVER_ERROR,
            ECError::Io(_)           => StatusCode::INTERNAL_SERVER_ERROR,
        }
    }
}
