// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\tests\test_cli.rs
//! CLI バイナリ `main_ack` の統合テスト
//! 生成した本物の署名で ACK JSON を作り、TTL 内で成功することを確認する。

use assert_cmd::Command;
use chrono::Utc;
use ed25519_dalek::{SigningKey, VerifyingKey, Signature, Signer};
use rand::rngs::OsRng;
use serde_json::json;
use std::fs;
use std::io::Write;
use tempfile::NamedTempFile;

fn make_valid_ack_json(id: &str) -> String {
    // ── 鍵生成 ─────────────────────────────────────────
    let sk = SigningKey::generate(&mut OsRng);
    let vk: VerifyingKey = (&sk).into();

    // ── canonical JSON 文字列 ─────────────────────────
    let ts = Utc::now();
    let payload = json!({
        "id": id,
        "timestamp": ts.to_rfc3339()
    })
    .to_string();

    // ── 署名（Base58） ───────────────────────────────
    let sig: Signature = sk.sign(payload.as_bytes());
    let sig_b58 = bs58::encode(sig.to_bytes()).into_string();
    let pk_b58  = bs58::encode(vk.to_bytes()).into_string();

    // ── 完整 ACK JSON ───────────────────────────────
    json!({
        "id": id,
        "timestamp": ts.to_rfc3339(),
        "signature": sig_b58,
        "pubkey": pk_b58
    })
    .to_string()
}

#[test]
fn cli_happy_path() {
    // ① ACK JSON を一時ファイルへ
    let mut tmp = NamedTempFile::new().expect("tmp file");
    let ack_json = make_valid_ack_json("abc123");
    write!(tmp, "{}", ack_json).unwrap();
    tmp.flush().unwrap(); // Windows でハンドルを閉じなくても OK

    // ② CLI 起動（--input <file> --ttl 3600）
    let mut cmd = Command::cargo_bin("main_ack").unwrap();
    cmd.args([
        "--input",
        tmp.path().to_str().unwrap(),
        "--ttl",
        "3600",
    ]);

    // ③ 成功を期待
    cmd.assert().success();
}
