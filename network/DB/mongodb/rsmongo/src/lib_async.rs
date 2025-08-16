// File: network/DB/mongodb/rsmongo/src/lib_async.rs
//
// Patched version: Transparent AES-GCM encryption/decryption of `content` field for testing.
// In production, use libmongocrypt FFI + NTRU unwrap.

use mongodb::{
    bson::{self, doc, Bson},
    error::Result,
    options::{ClientOptions, ReadPreference, ReadPreferenceOptions, SelectionCriteria},
    Client, Collection, Database,
};
use serde::{Deserialize, Serialize};
use futures::stream::TryStreamExt;
use std::time::Duration as StdDuration;

// ---------- simple AES-GCM helper (testing only) ----------
use ring::aead::{Aad, LessSafeKey, Nonce, UnboundKey, AES_256_GCM};
use ring::rand::{SecureRandom, SystemRandom};
static RNG: SystemRandom = SystemRandom::new();

fn encrypt_field(plaintext: &[u8], dek: &[u8; 32]) -> Vec<u8> {
    let mut nonce_bytes = [0u8; 12];
    RNG.fill(&mut nonce_bytes).unwrap();
    let nonce = Nonce::assume_unique_for_key(nonce_bytes);
    let key = LessSafeKey::new(UnboundKey::new(&AES_256_GCM, dek).unwrap());
    let mut in_out = plaintext.to_vec();
    key.seal_in_place_append_tag(nonce, Aad::empty(), &mut in_out).unwrap();
    let mut out = nonce_bytes.to_vec();
    out.extend(in_out);
    out
}

fn decrypt_field(cipher: &[u8], dek: &[u8; 32]) -> Option<Vec<u8>> {
    if cipher.len() < 12 { return None; }
    let (nonce_bytes, ct) = cipher.split_at(12);
    let nonce = Nonce::assume_unique_for_key(<[u8;12]>::try_from(nonce_bytes).unwrap());
    let key = LessSafeKey::new(UnboundKey::new(&AES_256_GCM, dek).unwrap());
    let mut buf = ct.to_vec();
    key.open_in_place(nonce, Aad::empty(), &mut buf).ok()?;
    let tag_len = 16;
    buf.truncate(buf.len() - tag_len);
    Some(buf)
}

fn load_dek() -> [u8; 32] {
    // Demo: load from env var BASE64_DEK; in prod unwrap NTRU capsule
    let b64 = std::env::var("BASE64_DEK").unwrap_or_default();
    let bytes = base64::decode(b64).unwrap_or_else(|_| vec![0u8; 32]);
    <[u8;32]>::try_from(bytes.as_slice()).unwrap_or([0u8;32])
}

pub struct MongoDBAsyncHandler {
    db: Database,
    dek: [u8; 32],
}

impl MongoDBAsyncHandler {
    pub async fn new(uri: &str, dbname: &str) -> Result<Self> {
        let mut opts = ClientOptions::parse(uri).await?;
        opts.connect_timeout = Some(StdDuration::from_secs(5));
        opts.server_selection_timeout = Some(StdDuration::from_secs(5));
        let client = Client::with_options(opts)?;
        Ok(Self { db: client.database(dbname), dek: load_dek() })
    }

    pub async fn new_with_read_preference(uri: &str, dbname: &str) -> Result<Self> {
        let mut opts = ClientOptions::parse(uri).await?;
        opts.selection_criteria = Some(SelectionCriteria::ReadPreference(
            ReadPreference::SecondaryPreferred { options: ReadPreferenceOptions::default() }
        ));
        let client = Client::with_options(opts)?;
        Ok(Self { db: client.database(dbname), dek: load_dek() })
    }

    // ------------ helper ------------
    fn validate_doc<T: serde::Serialize>(_doc: &T) -> Result<()> {
        // Int32 / float check can be inserted here.
        Ok(())
    }

    pub async fn insert_document<T>(&self, coll: &str, mut doc: T) -> Result<mongodb::bson::oid::ObjectId>
    where T: Serialize + Deserialize<'static> + Clone {
        Self::validate_doc(&doc)?;
        // content フィールド暗号化
        if let Ok(mut d) = bson::to_document(&doc) {
            if let Some(Bson::String(content)) = d.get("content") {
                let cipher = encrypt_field(content.as_bytes(), &self.dek);
                d.insert("content", Bson::Binary(bson::Binary {
                    subtype: bson::spec::BinarySubtype::Generic,
                    bytes: cipher
                }));
                doc = bson::from_document(d)?;
            }
        }
        let collection: Collection<T> = self.db.collection(coll);
        let res = collection.insert_one(doc, None).await?;
        Ok(res.inserted_id.as_object_id().unwrap())
    }

    pub async fn find_document<T>(&self, coll: &str, query: bson::Document) -> Result<Option<T>>
    where T: DeserializeOwned {
        let collection: Collection<T> = self.db.collection(coll);
        if let Some(mut d) = collection.find_one(query, None).await? {
            // decrypt
            if let Ok(mut raw) = bson::to_document(&d) {
                if let Some(Bson::Binary(bin)) = raw.get("content") {
                    if let Some(pt) = decrypt_field(&bin.bytes, &self.dek) {
                        raw.insert("content", String::from_utf8_lossy(&pt).to_string());
                        d = bson::from_document(raw)?;
                    }
                }
            }
            Ok(Some(d))
        } else { Ok(None) }
    }

    pub async fn list_documents<T>(&self, coll: &str) -> Result<Vec<T>>
    where T: DeserializeOwned + Serialize {
        let collection: Collection<T> = self.db.collection(coll);
        let mut cur = collection.find(None, None).await?;
        let mut out = Vec::new();
        while let Some(mut d) = cur.try_next().await? {
            // decrypt per doc
            if let Ok(mut raw) = bson::to_document(&d) {
                if let Some(Bson::Binary(bin)) = raw.get("content") {
                    if let Some(pt) = decrypt_field(&bin.bytes, &self.dek) {
                        raw.insert("content", String::from_utf8_lossy(&pt).to_string());
                        d = bson::from_document(raw)?;
                    }
                }
            }
            out.push(d);
        }
        Ok(out)
    }
}
