// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\src\main_ack.rs
// src/main_ack.rs

//! CLI 用バイナリ: ACK の署名検証＋TTL（有効期限）チェックを行うツール
//!
//! Usage:
//! ```bash
//! poh-ack \
//!   --input path/to/ack.json \
//!   --ttl 300
//! ```
//!
//! 入力ファイルは JSON 形式で、少なくとも以下のフィールドを持つ必要があります:
//! {
//!   "id": "トランザクション ID",
//!   "timestamp": "RFC3339 形式のタイムスタンプ",
//!   "signature": "Base58-encoded Ed25519 signature",
//!   "pubkey": "Base58-encoded Ed25519 public key"
//! }

use clap::Parser;
use chrono::Utc;
use std::fs;
use serde_json::from_str;
use poh_ack_rust::{Ack, AckError};

/// CLI 引数定義
#[derive(Parser)]
#[command(name = "poh-ack", about = "Verify ACK signature and TTL")]
struct Args {
    /// JSON file containing {id, timestamp, signature, pubkey}
    #[arg(long)]
    input: String,

    /// TTL (有効期限) in seconds
    #[arg(long, default_value = "300")]
    ttl: i64,
}

#[tokio::main]
async fn main() -> Result<(), AckError> {
    // コマンドライン引数をパース
    let args = Args::parse();

    // ファイル読み込み（IO エラーは AckError::Io にマッピングされます）
    let data = fs::read_to_string(&args.input)?;

    // JSON デシリアライズ（エラーは AckError::Deserialize にマッピングされます）
    let ack: Ack = from_str(&data)?;

    // 署名検証＋TTL 検証
    //    verify(ttl_seconds) が両者を一度にチェック
    ack.verify(args.ttl)?;

    // 成功時
    println!("ACK '{}' is valid and within {} seconds TTL", ack.id, args.ttl);
    Ok(())
}
