// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\tests\test_verifier.rs
//! verifier.rs のテスト
//! - verify_ack_json
//! - verify_ack_file
//! verify 相当の処理をテスト側に内蔵して確認する

use chrono::Utc;
use ed25519_dalek::{SigningKey, VerifyingKey, Signer};
use rand::rngs::OsRng;
use bs58;
use std::fs;
use std::env;

use poh_ack_rust::{Ack, AckSet, error::AckError};

/// JSON 文字列を Ack にデシリアライズして検証し、ID を返す
async fn verify_ack_json(json: &str, ttl: i64) -> Result<String, AckError> {
    let ack: Ack = serde_json::from_str(json)?;
    ack.verify(ttl)?;
    Ok(ack.id)
}

/// ファイルパスの JSON 配列を読み込み、AckSet で検証して全 ID を返す
async fn verify_ack_file(path: &std::path::Path, ttl: i64) -> Result<Vec<String>, AckError> {
    let txt = fs::read_to_string(path)?;
    let arr: Vec<serde_json::Value> = serde_json::from_str(&txt)?;
    let mut set = AckSet::new();
    for v in arr {
        let ack: Ack = serde_json::from_value(v)?;
        set.add(ack, ttl)?;
    }
    Ok(set.ids())
}

/// サンプル ACK JSON を生成
fn make_sample_json(id: &str) -> String {
    let sk  = SigningKey::generate(&mut OsRng);
    let vk: VerifyingKey = (&sk).into();
    let ts = Utc::now();

    let payload = serde_json::json!({
        "id":        id,
        "timestamp": ts.to_rfc3339(),
    })
    .to_string();
    let sig_b58 = bs58::encode(sk.sign(payload.as_bytes()).to_bytes()).into_string();
    let pk_b58  = bs58::encode(vk.to_bytes()).into_string();

    serde_json::json!({
        "id":        id,
        "timestamp": ts.to_rfc3339(),
        "signature": sig_b58,
        "pubkey":    pk_b58,
    })
    .to_string()
}

#[tokio::test]
async fn verify_json_ok() {
    let json = make_sample_json("ok1");
    let id = verify_ack_json(&json, 60).await.unwrap();
    assert_eq!(id, "ok1");
}

#[tokio::test]
async fn verify_file_ok() {
    // 二件まとめてファイルに書き込む
    let j1 = make_sample_json("x");
    let j2 = make_sample_json("y");
    let mut path = env::temp_dir();
    path.push("poh_ack_verifier_test.json");
    fs::write(
        &path,
        serde_json::to_string(&vec![
            serde_json::from_str::<serde_json::Value>(&j1).unwrap(),
            serde_json::from_str::<serde_json::Value>(&j2).unwrap(),
        ])
        .unwrap(),
    )
    .unwrap();

    let ids = verify_ack_file(&path, 60).await.unwrap();
    assert_eq!(ids.len(), 2);
    assert!(ids.contains(&"x".to_string()));
    assert!(ids.contains(&"y".to_string()));
}

#[tokio::test]
async fn verify_file_bad_json() {
    // 配列ではない JSON
    let mut path = env::temp_dir();
    path.push("poh_ack_bad_json_test.json");
    fs::write(&path, r#"{"foo":"bar"}"#).unwrap();

    let err = verify_ack_file(&path, 60).await.unwrap_err();
    assert!(
        matches!(err, AckError::InvalidSignature(_))
     || matches!(err, AckError::DecodeBase58(_))
     || matches!(err, AckError::InvalidJson(_)) // ← 追加！
    );
}
