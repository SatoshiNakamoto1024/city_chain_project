// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\benches\bench_verifier.rs
//! Criterion ベンチ ― Ack::verify (署名 + TTL) 性能測定
//! ------------------------------------------------------
//! `cargo bench --bench bench_verifier` で実行してください。
//! - *debug* ビルドではなく **release** ビルドになる点に注意。
//!
//! 署名が通らないとベンチにならないため、ここでテスト用に
//! 1. Ed25519 鍵ペアを生成
//! 2. Ack の「canonical JSON」ペイロードを署名
//! 3. 公開鍵 / 署名を Base58 でエンコード
//! をワンショットで行い、毎回同じ（正当な）Ack を使って計測します。
//! ------------------------------------------------------
//! Criterion ベンチ ― Ack::verify 性能測定
//! ----------------------------------------
//! 実行: `cargo bench --bench bench_verifier`

use chrono::Utc;
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use ed25519_dalek::{Signature, SigningKey, Signer, VerifyingKey};
use once_cell::sync::Lazy;
use poh_ack_rust::Ack;
use rand::rngs::OsRng;          // ← rand_core ではなく rand 経由で OK

// ─── 1. 一度だけテスト用 Ack を生成 ───────────────────────────────
static SAMPLE_ACK: Lazy<Ack> = Lazy::new(|| {
    // キーペア生成（rand_core feature が有効なので generate が使える）
    let sk: SigningKey   = SigningKey::generate(&mut OsRng);
    let vk: VerifyingKey = (&sk).into();

    // canonical JSON
    let id = "bench_tx".to_owned();
    let ts = Utc::now();
    let payload = serde_json::json!({
        "id":        id,
        "timestamp": ts.to_rfc3339(),
    })
    .to_string();

    // 署名
    let sig: Signature = sk.sign(payload.as_bytes());

    // Ack 構築（Base58 エンコード）
    Ack {
        id,
        timestamp: ts,
        signature: bs58::encode(sig.to_bytes()).into_string(),
        pubkey:    bs58::encode(vk.to_bytes()).into_string(),
    }
});

// ─── 2. Criterion ベンチ関数 ───────────────────────────────────────
fn bench_verify(c: &mut Criterion) {
    const TTL_SEC: i64 = 300; // 5 分

    c.bench_function("Ack::verify", |b| {
        b.iter(|| {
            let ack = black_box(&*SAMPLE_ACK);
            ack.verify(TTL_SEC).unwrap();
        })
    });
}

criterion_group!(benches, bench_verify);
criterion_main!(benches);
