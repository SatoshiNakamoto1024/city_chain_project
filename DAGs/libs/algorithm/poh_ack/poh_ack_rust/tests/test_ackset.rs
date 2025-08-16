// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\tests\test_ackset.rs
//! AckSet の動作検証
//! - 同期 add
//! - 非同期 add_async / add_batch_async
//! - 重複エラー
//! - TTL エラー

use chrono::{Duration, Utc};
use ed25519_dalek::{SigningKey, VerifyingKey, Signer};
use rand::rngs::OsRng;
use bs58;

use poh_ack_rust::{Ack, AckSet, error::AckError};

/// テスト用 ACK を組み立てるユーティリティ
fn make_ack(id: &str, ts: chrono::DateTime<Utc>) -> Ack {
    // Ed25519 鍵ペア生成
    let sk  = SigningKey::generate(&mut OsRng);
    let vk: VerifyingKey = (&sk).into();

    // canonical JSON を作って署名
    let payload = serde_json::json!({
        "id":        id,
        "timestamp": ts.to_rfc3339(),
    })
    .to_string();
    let sig     = sk.sign(payload.as_bytes());
    let sig_b58 = bs58::encode(sig.to_bytes()).into_string();
    let pk_b58  = bs58::encode(vk.to_bytes()).into_string();

    Ack {
        id:        id.to_string(),
        timestamp: ts,
        signature: sig_b58,
        pubkey:    pk_b58,
    }
}

#[test]
fn add_and_ids_sync() {
    let mut set = AckSet::new();
    let ack = make_ack("x1", Utc::now());
    assert!(set.add(ack, 300).is_ok());
    assert_eq!(set.ids(), vec!["x1".to_string()]);
}

#[test]
fn add_duplicate_sync() {
    let mut set = AckSet::new();
    let ack = make_ack("dup", Utc::now());
    assert!(set.add(ack.clone(), 60).is_ok());
    let err = set.add(ack, 60).unwrap_err();
    assert!(matches!(err, AckError::DuplicateId(_)));
}

#[test]
fn ttl_error_sync() {
    let mut set = AckSet::new();
    let old = Utc::now() - Duration::seconds(120);
    let ack = make_ack("t", old);
    let err = set.add(ack, 30).unwrap_err();
    assert!(matches!(err, AckError::TtlExpired(_)));
}

#[tokio::test]
async fn add_async_and_batch() {
    let mut set = AckSet::new();
    let now = Utc::now();

    // 非同期単一追加
    set.add_async(make_ack("a1", now), 60).await.unwrap();

    // 非同期バッチ追加
    set.add_batch_async(
        vec![ make_ack("b2", now), make_ack("c3", now) ],
        60
    )
    .await
    .unwrap();

    let mut ids = set.ids();
    ids.sort();
    assert_eq!(ids, ["a1".to_string(), "b2".to_string(), "c3".to_string()]);
}

#[tokio::test]
async fn add_async_duplicate() {
    let mut set = AckSet::new();
    let ack = make_ack("dup", Utc::now());
    set.add_async(ack.clone(), 60).await.unwrap();
    let err = set.add_async(ack, 60).await.unwrap_err();
    assert!(matches!(err, AckError::DuplicateId(_)));
}
