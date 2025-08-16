// D:\city_chain_project\DAGs\libs\algorithm\poh_ack\poh_ack_rust\src\ackset.rs
// src/ackset.rs
//! ACK の集合管理モジュール
//! - 単一 ACK の検証（署名＋TTL）
//! - 同期／非同期版の add メソッド
//! - 重複チェック
//! - ID 一覧取得

use chrono::{DateTime, Utc};
use ed25519_dalek::{
    VerifyingKey, Signature, Verifier, PUBLIC_KEY_LENGTH, SIGNATURE_LENGTH,
};
use serde::{Deserialize, Serialize};
use bs58;
use tokio::task;

use crate::error::AckError;
use crate::ttl::validate_ttl;

/// 単一の ACK メッセージ
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Ack {
    /// トランザクション ID
    pub id: String,
    /// 発行時刻 (ISO8601 / UTC)
    pub timestamp: DateTime<Utc>,
    /// Base58(Ed25519 署名)
    pub signature: String,
    /// Base58(公開鍵)
    pub pubkey: String,
}

impl Ack {
    // ──────────────────────────────────────────────────────────────
    // JSON → Ack 変換ヘルパ
    //   * 破損した JSON は AckError::InvalidJson に変換
    //   * Smoke‑test やファイル検証で利用される
    // ──────────────────────────────────────────────────────────────
    pub fn from_json(json: &str) -> Result<Ack, AckError> {
        serde_json::from_str(json).map_err(AckError::InvalidJson)
    }

    /// 検証用の「canonical JSON」を生成
    /// {"id":"...","timestamp":"..."}
    fn canonical_payload(&self) -> String {
        let mut map = serde_json::Map::with_capacity(2);
        map.insert("id".into(), serde_json::Value::String(self.id.clone()));
        map.insert(
            "timestamp".into(),
            serde_json::Value::String(self.timestamp.to_rfc3339()),
        );
        serde_json::Value::Object(map).to_string()
    }

    /// 署名検証のみ
    pub fn verify_signature(&self) -> Result<(), AckError> {
        // 公開鍵デコード
        let pk_bytes = bs58::decode(&self.pubkey)
            .into_vec()
            .map_err(|e| AckError::DecodeBase58(e.to_string()))?;
        if pk_bytes.len() != PUBLIC_KEY_LENGTH {
            return Err(AckError::InvalidKeyLength(pk_bytes.len()));
        }
        let mut pk_arr = [0u8; PUBLIC_KEY_LENGTH];
        pk_arr.copy_from_slice(&pk_bytes);
        let vk = VerifyingKey::from_bytes(&pk_arr)
            .map_err(|e| AckError::InvalidPublicKey(e.to_string()))?;

        // 署名デコード
        let sig_bytes = bs58::decode(&self.signature)
            .into_vec()
            .map_err(|e| AckError::DecodeBase58(e.to_string()))?;
        if sig_bytes.len() != SIGNATURE_LENGTH {
            return Err(AckError::InvalidSignatureLength(sig_bytes.len()));
        }
        let mut sig_arr = [0u8; SIGNATURE_LENGTH];
        sig_arr.copy_from_slice(&sig_bytes);
        let signature = Signature::from_bytes(&sig_arr);

        // 検証
        vk.verify(self.canonical_payload().as_bytes(), &signature)
            .map_err(|e| AckError::SignatureVerification(e.to_string()))
    }

    /// TTL 検証のみ
    pub fn verify_ttl(&self, ttl_seconds: i64) -> Result<(), AckError> {
        validate_ttl(&self.timestamp, ttl_seconds)
    }

    /// 署名＋TTL の完全検証
    pub fn verify(&self, ttl_seconds: i64) -> Result<(), AckError> {
        self.verify_signature()?;
        self.verify_ttl(ttl_seconds)?;
        Ok(())
    }

    /// 非同期版 verify（ブロッキング処理を別スレッドで実行）
    pub async fn verify_async(&self, ttl_seconds: i64) -> Result<(), AckError> {
        // self を先にクローンして所有オブジェクトを作る
        let ack = self.clone();
        // spawn_blocking は 'static クロージャーを要求するので、
        // ack（Ack 型）だけをムーブキャプチャ
        let join_result = task::spawn_blocking(move || ack.verify(ttl_seconds))
            .await
            .map_err(|e| AckError::InternalError(e.to_string()))?;
        // クロージャー内部の Result を展開して返す
        join_result
    }
}

/// ACK の集合
#[derive(Debug, Default, Clone)]
pub struct AckSet {
    acks: Vec<Ack>,
}

impl AckSet {
    /// 新規セットを作成
    pub fn new() -> Self {
        AckSet { acks: Vec::new() }
    }

    /// 同期的に ACK を追加して検証
    /// - 重複 ID は Err(AckError::DuplicateId) を返す
    pub fn add(&mut self, ack: Ack, ttl_seconds: i64) -> Result<(), AckError> {
        if self.acks.iter().any(|a| a.id == ack.id) {
            return Err(AckError::DuplicateId(ack.id));
        }
        ack.verify(ttl_seconds)?;
        self.acks.push(ack);
        Ok(())
    }

    /// 非同期的に ACK を追加して検証
    pub async fn add_async(&mut self, ack: Ack, ttl_seconds: i64) -> Result<(), AckError> {
        // 1) バックグラウンドで署名＋TTL を検証し、検証済みの Ack を返す
        let verified_ack = task::spawn_blocking(move || {
            ack.verify(ttl_seconds)?;
            Ok::<Ack, AckError>(ack)
        })
        .await
        .map_err(|e| AckError::InternalError(e.to_string()))?
        ?; // ここで Ack を得る

        // 2) 重複チェック＆追加（メインスレッド）
        if self.acks.iter().any(|a| a.id == verified_ack.id) {
            return Err(AckError::DuplicateId(verified_ack.id.clone()));
        }
        self.acks.push(verified_ack);
        Ok(())
    }

    /// 非同期一括追加（順次 await）
    pub async fn add_batch_async<I>(
        &mut self,
        acks: I,
        ttl_seconds: i64,
    ) -> Result<(), AckError>
    where
        I: IntoIterator<Item = Ack>,
    {
        for ack in acks {
            self.add_async(ack, ttl_seconds).await?;
        }
        Ok(())
    }

    /// 全 ID を返す
    pub fn ids(&self) -> Vec<String> {
        self.acks.iter().map(|a| a.id.clone()).collect()
    }

    /// 登録件数
    pub fn len(&self) -> usize {
        self.acks.len()
    }

    /// 空かどうか
    pub fn is_empty(&self) -> bool {
        self.acks.is_empty()
    }

    /// 全クリア
    pub fn clear(&mut self) {
        self.acks.clear();
    }
}
