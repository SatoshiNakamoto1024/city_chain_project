// \city_chain_project\network\DB\mongodb\rsmongo\src/bin/main_rsmongodb.rs

use rsmongodb::lib_async::{MongoDBAsyncHandler, ensure_ttl_6months};
use mongodb::bson::{doc, Bson, Document, DateTime as BsonDateTime};
use tokio::{signal, sync::mpsc};
use std::{collections::HashMap, fs};
use serde_json::Value as Json;

/// Writer へ送るチャネル
type TxSender = mpsc::Sender<Document>;

/// 大陸ごとの非同期 Writer ハブ
pub struct Writers {
    senders: HashMap<String, TxSender>, // "asia" -> その大陸の writer への送信口
}

impl Writers {
    /// DAG からの書き込み依頼を即時キューイング（ノンブロッキング）
    pub fn enqueue(&self, continent: &str, mut doc: Document) {
        if !doc.contains_key("createdAt") {
            doc.insert("createdAt", Bson::DateTime(BsonDateTime::now()));
        }
        if let Some(tx) = self.senders.get(continent) {
            // 投げられない場合（満杯）には、上位でリトライ戦略を検討
            let _ = tx.try_send(doc);
        }
    }
}

/// JSON から「大陸 -> URI」マップを読み込む（Atlas 用）
fn load_continental_uris_from_json() -> HashMap<String, String> {
    // 既存ファイルを読みます
    let p = "/home/satoshi/work/city_chain_project/network/DB/config/mongodb_config/main_chain/continental_mongodb_config/mongodb_continental.json";
    let s = fs::read_to_string(p).expect("read mongodb_continental.json");
    let v: Json = serde_json::from_str(&s).expect("parse mongodb_continental.json");
    let table = v.get("complete").and_then(|x| x.as_object()).expect("complete is object");

    let mut uris = HashMap::new();
    for (k, val) in table {
        if let Some(uri) = val.as_str() {
            uris.insert(k.to_string(), uri.to_string());
        }
    }
    uris
}

/// 各大陸ごとに Writer タスクを起動（MongoDB クライアントを持ち、MPSC を受信して書き込む）
async fn start_writers(uris: &HashMap<String, String>, dbname: &str, coll_name: &str) -> Writers {
    let mut senders = HashMap::new();

    for (continent, uri) in uris {
        // 送信用チャネルを作成（十分なバッファ）
        let (tx, mut rx) = mpsc::channel::<Document>(10_000);
        senders.insert(continent.clone(), tx);

        // 各大陸に対応する MongoDB ハンドラ（プライマリ書き込み用）
        let handler = MongoDBAsyncHandler::new(uri, dbname)
            .await
            .unwrap_or_else(|e| panic!("create handler for {} failed: {:?}", continent, e));

        // TTL（6ヶ月）インデックスを念のため作成（存在すれば no-op）
        let coll_for_ttl = handler.db().collection::<Document>(coll_name);
        ensure_ttl_6months(&coll_for_ttl)
            .await
            .expect("create TTL index");

        // 受信ループ：ドキュメントを受けるたびに暗号化処理を含む insert を実行
        let coll = coll_name.to_string();
        tokio::spawn(async move {
            while let Some(doc) = rx.recv().await {
                if let Err(e) = handler.insert_document(&coll, doc).await {
                    eprintln!("[writer:{}] insert error: {:?}", coll, e);
                    // TODO: 死活監視・DLQ などの実装余地
                }
            }
        });
    }

    Writers { senders }
}

#[tokio::main]
async fn main() -> mongodb::error::Result<()> {
    // ==== 設定の読み込み ====
    // DB 名は環境変数で上書き可能（未設定なら city_chain）
    let dbname = std::env::var("MONGODB_DB").unwrap_or_else(|_| "city_chain".to_string());
    // コレクション名は固定（必要なら env で可変に）
    let coll = std::env::var("MONGODB_COLL").unwrap_or_else(|_| "transactions".to_string());

    // 大陸 -> URI の一覧を JSON から読み込む（本番想定）
    let uris = load_continental_uris_from_json();

    // ==== Writer 群（大陸ごと）を起動 ====
    let writers = start_writers(&uris, &dbname, &coll).await;
    println!(
        "[service] writers started for {} continents (db='{}', coll='{}')",
        writers.senders.len(),
        dbname,
        coll
    );

    // ==== デモ（任意） ====
    if std::env::var("RUN_DEMO").ok().as_deref() == Some("1") {
        let d1 = doc!{ "sender":"A", "receiver":"B", "amount": 10, "status":"pending" };
        let d2 = doc!{ "sender":"C", "receiver":"D", "amount": 20, "status":"completed" };
        writers.enqueue("asia", d1);
        writers.enqueue("europe", d2);
        println!("[demo] enqueued 2 docs");
    }

    // ==== Ctrl+C まで常駐 ====
    println!("[service] ready. Press Ctrl+C to stop.");
    signal::ctrl_c().await.expect("failed to listen for ctrl_c");
    println!("[service] shutting down…");
    Ok(())
}
