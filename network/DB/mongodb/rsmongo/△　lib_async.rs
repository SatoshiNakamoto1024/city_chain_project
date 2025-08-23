// \city_chain_project/network/DB/mongodb/rsmongo/src/lib_async.rs

use mongodb::{
    bson::{self, doc, Bson, Document},
    error::Result,
    options::{
        ClientOptions, ReadPreference, ReadPreferenceOptions, SelectionCriteria, IndexOptions, WriteConcern, Acknowledgment,
    },
    Client, Collection, Database, IndexModel, // ← IndexModel は options ではなく crate 直下
};
use futures::stream::TryStreamExt;
use std::time::Duration as StdDuration;

// ---------- AES-GCM helper (testing only) ----------
use ring::aead::{Aad, LessSafeKey, Nonce, UnboundKey, AES_256_GCM};
use ring::rand::{SecureRandom, SystemRandom};
use once_cell::sync::Lazy;
use base64::{engine::general_purpose, Engine as _};

// ---------- Client シングルトン（URI + 読み取り方針ごとに共有） ----------
use std::collections::HashMap;
use tokio::sync::RwLock;

/// key 例:
///   "mongodb+srv://....|rp=pri"
///   "mongodb+srv://....|rp=sec"
static CLIENTS: Lazy<RwLock<HashMap<String, Client>>> = Lazy::new(|| RwLock::new(HashMap::new()));

static RNG: Lazy<SystemRandom> = Lazy::new(SystemRandom::new);

// ========== TTL Index ==========

// 任意フィールドに任意秒数の TTL を設定（存在すれば no-op）
pub async fn ensure_ttl(
    coll: &mongodb::Collection<mongodb::bson::Document>,
    field: &str,
    expire_secs: u64,
    name: Option<&str>,
) -> mongodb::error::Result<()> {
    let idx_name = name
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("ttl_{}_{}s", field, expire_secs));

    let opts = IndexOptions::builder()
        .expire_after(Some(StdDuration::from_secs(expire_secs)))
        .name(Some(idx_name))
        .build();

    let model = IndexModel::builder()
        .keys(doc! { field: 1 })
        .options(opts)
        .build();

    coll.create_index(model, None).await?;
    Ok(())
}

// 6ヶ月のショートカット（フィールド指定版）
pub async fn ensure_ttl_6months_on(
    coll: &mongodb::Collection<mongodb::bson::Document>,
    field: &str,
) -> mongodb::error::Result<()> {
    // 約6ヶ月（30日×6 = 180日）
    let six_months = 60 * 60 * 24 * 30 * 6;
    // インデックス名は "ttl_<field>_6m" に
    ensure_ttl(coll, field, six_months, Some(&format!("ttl_{}_6m", field))).await
}

// 既存互換（フィールド固定: createdAt）
pub async fn ensure_ttl_6months(
    coll: &mongodb::Collection<mongodb::bson::Document>,
) -> mongodb::error::Result<()> {
    ensure_ttl_6months_on(coll, "createdAt").await
}

// ========== 暗号化ユーティリティ ==========
fn encrypt_field(plaintext: &[u8], dek: &[u8; 32]) -> Vec<u8> {
    let mut nonce_bytes = [0u8; 12];
    RNG.fill(&mut nonce_bytes).unwrap();
    let nonce = Nonce::assume_unique_for_key(nonce_bytes);
    let key = LessSafeKey::new(UnboundKey::new(&AES_256_GCM, dek).unwrap());
    let mut in_out = plaintext.to_vec();
    key.seal_in_place_append_tag(nonce, Aad::empty(), &mut in_out)
        .unwrap();
    let mut out = nonce_bytes.to_vec();
    out.extend(in_out);
    out
}

fn decrypt_field(cipher: &[u8], dek: &[u8; 32]) -> Option<Vec<u8>> {
    if cipher.len() < 12 {
        return None;
    }
    let (nonce_bytes, ct) = cipher.split_at(12);
    let nonce =
        Nonce::assume_unique_for_key(<[u8; 12]>::try_from(nonce_bytes).unwrap());
    let key = LessSafeKey::new(UnboundKey::new(&AES_256_GCM, dek).unwrap());
    let mut buf = ct.to_vec();
    key.open_in_place(nonce, Aad::empty(), &mut buf).ok()?;
    let tag_len = 16;
    if buf.len() < tag_len {
        return None;
    }
    buf.truncate(buf.len() - tag_len);
    Some(buf)
}

fn load_dek() -> [u8; 32] {
    let b64 = std::env::var("BASE64_DEK").unwrap_or_default();
    let bytes = general_purpose::STANDARD
        .decode(b64)
        .unwrap_or_else(|_| vec![0u8; 32]);
    <[u8; 32]>::try_from(bytes.as_slice()).unwrap_or([0u8; 32])
}

// ========== Client 構築（プール・タイムアウト・読み取り方針の込み）===========

/// 接続プールやタイムアウト、読み取り方針（セカンダリ優先か）の設定値をまとめて構築。
async fn build_client(uri: &str, secondary_preferred: bool) -> Result<Client> {
    let mut opts = ClientOptions::parse(uri).await?;

    // ---- タイムアウト（既存のまま）----
    let connect_ms: u64 = std::env::var("MONGO_CONNECT_MS").ok()
        .and_then(|v| v.parse().ok()).unwrap_or(5_000);
    let sst_ms: u64 = std::env::var("MONGO_SST_MS").ok()
        .and_then(|v| v.parse().ok()).unwrap_or(15_000);

    opts.connect_timeout = Some(StdDuration::from_millis(connect_ms));
    opts.server_selection_timeout = Some(StdDuration::from_millis(sst_ms));

    // ---- プールチューニング（環境変数で上書き可） ----
    let mut max_pool: u32 = 200;
    let mut min_pool: u32 = 20;
    let mut max_idle_ms: u64 = 60_000; // idle保持上限

    if let Ok(v) = std::env::var("MONGO_POOL_MAX") {
        if let Ok(n) = v.parse() { max_pool = n; }
    }
    if let Ok(v) = std::env::var("MONGO_POOL_MIN") {
        if let Ok(n) = v.parse() { min_pool = n; }
    }
    if let Ok(v) = std::env::var("MONGO_POOL_IDLE_MS") {
        if let Ok(n) = v.parse() { max_idle_ms = n; }
    }

    opts.max_pool_size = Some(max_pool);
    opts.min_pool_size = Some(min_pool);
    opts.max_idle_time = Some(StdDuration::from_millis(max_idle_ms));

    // ✅ 送金などトランザクション系は安全寄り：多数派ACKを既定に
    opts.write_concern = Some(
        WriteConcern::builder()
            .w(Acknowledgment::Majority)   // ← enum を渡す
            .build()
    );

    // ---- 読み取りポリシー ----
    if secondary_preferred {
        opts.selection_criteria = Some(SelectionCriteria::ReadPreference(
            ReadPreference::SecondaryPreferred { options: ReadPreferenceOptions::default() },
        ));
    }

    let client = Client::with_options(opts)?;
    Ok(client)
}

/// URI + 読み取り方針単位で `Client` をシングルトン共有。
async fn get_or_init_client(uri: &str, secondary_preferred: bool) -> Result<Client> {
    let key = format!(
        "{}|rp={}",
        uri,
        if secondary_preferred { "sec" } else { "pri" }
    );

    // まず read ロック（ヒットしたら即返す）
    {
        let map = CLIENTS.read().await;
        if let Some(c) = map.get(&key) {
            return Ok(c.clone()); // mongodb::Client は Clone（ハンドル）
        }
    }

    // なければ build → write ロックで登録（二重初期化回避のため再確認）
    let client_built = build_client(uri, secondary_preferred).await?;

    let mut map = CLIENTS.write().await;
    if let Some(c) = map.get(&key) {
        return Ok(c.clone());
    }
    map.insert(key, client_built.clone());
    Ok(client_built)
}

// ========== 既存のハンドラ ==========

pub struct MongoDBAsyncHandler {
    db: Database,
    dek: [u8; 32],
}

impl MongoDBAsyncHandler {
    /// プライマリ向け（書き込み）
    pub async fn new(uri: &str, dbname: &str) -> Result<Self> {
        let client = get_or_init_client(uri, false).await?;
        Ok(Self {
            db: client.database(dbname),
            dek: load_dek(),
        })
    }

    /// セカンダリ優先（読み取り）
    pub async fn new_with_read_preference(uri: &str, dbname: &str) -> Result<Self> {
        let client = get_or_init_client(uri, true).await?;
        Ok(Self {
            db: client.database(dbname),
            dek: load_dek(),
        })
    }

    /// Database ハンドル（必要ならテスト等で利用）
    pub fn db(&self) -> Database {
        self.db.clone()
    }

    fn coll(&self, name: &str) -> Collection<Document> {
        self.db.collection::<Document>(name)
    }

    /// content が String なら AES-GCM で暗号化して Binary で書き戻す
    fn maybe_encrypt_content(&self, d: &mut Document) {
        if let Some(Bson::String(s)) = d.get("content") {
            let cipher = encrypt_field(s.as_bytes(), &self.dek);
            d.insert(
                "content",
                Bson::Binary(bson::Binary {
                    subtype: bson::spec::BinarySubtype::Generic,
                    bytes: cipher,
                }),
            );
        }
    }

    /// Binary なら復号して String で書き戻す
    fn maybe_decrypt_content(&self, d: &mut Document) {
        if let Some(Bson::Binary(bin)) = d.get("content") {
            if let Some(pt) = decrypt_field(&bin.bytes, &self.dek) {
                d.insert("content", String::from_utf8_lossy(&pt).to_string());
            }
        }
    }

    // ---------- CRUD (Document 固定) ----------

    pub async fn insert_document(
        &self,
        coll: &str,
        mut doc: Document,
    ) -> Result<mongodb::bson::oid::ObjectId> {
        self.maybe_encrypt_content(&mut doc);
        let res = self.coll(coll).insert_one(doc, None).await?;
        Ok(res.inserted_id.as_object_id().unwrap())
    }

    pub async fn insert_document_with_retry(
        &self,
        coll: &str,
        doc: Document,
        max_retry: usize,
    ) -> Result<mongodb::bson::oid::ObjectId> {
        use tokio::time::{sleep, Duration};
        let mut last_err = None;
        for attempt in 0..max_retry {
            match self.insert_document(coll, doc.clone()).await {
                Ok(id) => return Ok(id),
                Err(e) => {
                    last_err = Some(e);
                    // NOTE: プール満杯時などは少し待って再試行（指数バックオフでもOK）
                    sleep(Duration::from_millis(50 * (attempt as u64 + 1))).await;
                }
            }
        }
        Err(last_err.unwrap())
    }

    pub async fn find_document(
        &self,
        coll: &str,
        query: Document,
    ) -> Result<Option<Document>> {
        if let Some(mut d) = self.coll(coll).find_one(query, None).await? {
            self.maybe_decrypt_content(&mut d);
            Ok(Some(d))
        } else {
            Ok(None)
        }
    }

    pub async fn list_documents(&self, coll: &str) -> Result<Vec<Document>> {
        let mut cur = self.coll(coll).find(None, None).await?;
        let mut out = Vec::new();
        while let Some(mut d) = cur.try_next().await? {
            self.maybe_decrypt_content(&mut d);
            out.push(d);
        }
        Ok(out)
    }

    pub async fn update_document(
        &self,
        coll: &str,
        filter: Document,
        mut update: Document,
    ) -> Result<i64> {
        // $set の中に content:String があれば暗号化する
        if let Some(Bson::Document(set_doc)) = update.get_mut("$set") {
            if let Some(Bson::String(s)) = set_doc.get("content") {
                let cipher = encrypt_field(s.as_bytes(), &self.dek);
                set_doc.insert(
                    "content",
                    Bson::Binary(bson::Binary {
                        subtype: bson::spec::BinarySubtype::Generic,
                        bytes: cipher,
                    }),
                );
            }
        }
        let res = self
            .coll(coll)
            .update_one(filter, update, None)
            .await?;
        Ok(res.modified_count as i64)
    }

    pub async fn delete_document(&self, coll: &str, filter: Document) -> Result<i64> {
        let res = self.coll(coll).delete_one(filter, None).await?;
        Ok(res.deleted_count as i64)
    }
}
