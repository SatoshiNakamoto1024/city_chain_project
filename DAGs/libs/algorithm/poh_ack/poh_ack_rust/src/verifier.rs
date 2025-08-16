// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\src\verifier.rs
//! 非同期 ACK 検証モジュール。
//! - JSON 文字列またはファイルから ACK を読み込み
//! - Ed25519 署名検証
//! - TTL チェック
//! - 成功すれば ID を返す

use std::path::Path;
use tokio::task;
use serde_json::{from_str, Value};
use crate::{ackset::AckSet, ttl::validate_ttl, error::AckError};
use crate::ackset::Ack;

/// JSON 文字列一件を非同期に検証し、ID を返す。
pub async fn verify_ack_json(json_str: &str, ttl_seconds: i64) -> Result<String, AckError> {
    // 1) JSON→Ack のパースはブロッキングで
    let ack: Ack = {
        let s = json_str.to_owned();
        task::spawn_blocking(move || {
            from_str::<Ack>(&s).map_err(|e| AckError::InvalidSignature(e.to_string()))
        })
        .await
        .map_err(|e| AckError::SignatureVerification(e.to_string()))??
    };

    // 2) 本体の verify + TTL チェックもブロッキングで
    task::spawn_blocking(move || {
        ack.verify()?;                               // 署名検証
        validate_ttl(&ack.timestamp, ttl_seconds)?;  // TTL 検証
        Ok(ack.id.clone())
    })
    .await
    .map_err(|e| AckError::SignatureVerification(e.to_string()))?
}

/// JSON 配列を含むファイルを非同期に読み込み、全 ACK を検証して ID リストを返す。
pub async fn verify_ack_file<P: AsRef<Path>>(path: P, ttl_seconds: i64) -> Result<Vec<String>, AckError> {
    // 1) ファイル読み込み
    let text = tokio::fs::read_to_string(path)
        .await
        .map_err(|e| AckError::DecodeBase58(e.to_string()))?;

    // 2) JSON 値としてパース
    let v: Value = from_str(&text)
        .map_err(|e| AckError::InvalidSignature(e.to_string()))?;
    let arr = v.as_array()
        .ok_or_else(|| AckError::InvalidSignature("ACK 配列ではありません".to_string()))?;

    // 3) AckSet を使って一括検証
    let mut set = AckSet::new();
    for item in arr {
        let ack: Ack = serde_json::from_value(item.clone())
            .map_err(|e| AckError::InvalidSignature(e.to_string()))?;
        set.add(ack)?;
    }
    Ok(set.ids())
}
