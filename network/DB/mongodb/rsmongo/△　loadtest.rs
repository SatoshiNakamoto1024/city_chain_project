// \city_chain_project\network\DB\mongodb\rsmongo\tests\loadtest.rs

use rsmongodb::lib_async::{MongoDBAsyncHandler, ensure_ttl_6months};

use mongodb::bson::{doc, Bson, Document, DateTime as BsonDateTime};
use serde_json::Value as Json;
use std::{fs, time::Instant};
use std::sync::Arc;

/// Atlas の大陸→URI を JSON から読み込む
fn load_uri_from_continental(continent: &str) -> String {
    let p = "/home/satoshi/work/city_chain_project/network/DB/config/mongodb_config/main_chain/continental_mongodb_config/mongodb_continental.json";
    let s = fs::read_to_string(p).expect("read mongodb_continental.json");
    let v: Json = serde_json::from_str(&s).expect("parse mongodb_continental.json");
    v["complete"][continent]
        .as_str()
        .unwrap_or_else(|| panic!("continent '{}' not found in config", continent))
        .to_string()
}

/// 単一大陸に対する書き込みレイテンシの負荷テスト
///
/// 環境変数:
/// - MONGODB_CONTINENT … "asia" など（既定 "asia"）
/// - MONGODB_DB        … 既定 "city_chain"
/// - MONGODB_COLL      … 既定 "transactions"
/// - LOAD_N            … 書き込み件数（既定 100）
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn loadtest_write_latency() -> mongodb::error::Result<()> {
    // ---- 設定の読み込み ----
    let continent = std::env::var("MONGODB_CONTINENT").unwrap_or_else(|_| "asia".to_string());
    let uri       = load_uri_from_continental(&continent);
    let dbname    = std::env::var("MONGODB_DB").unwrap_or_else(|_| "city_chain".to_string());
    let coll_name = std::env::var("MONGODB_COLL").unwrap_or_else(|_| "transactions".to_string());
    let n: usize  = std::env::var("LOAD_N").ok().and_then(|s| s.parse().ok()).unwrap_or(100);

    // ---- ハンドラ準備 & TTL（6ヶ月）インデックスを作成（存在すれば no-op）----
    let handler  = Arc::new(MongoDBAsyncHandler::new(&uri, &dbname).await?);
    let coll_ref = handler.db().collection::<Document>(&coll_name);
    ensure_ttl_6months(&coll_ref).await?;

    // ---- N 並列で insert を投げる ----
    let mut tasks = Vec::with_capacity(n);
    for i in 0..n {
        let h = handler.clone();
        let coll = coll_name.clone();
        tasks.push(tokio::spawn(async move {
            let doc = doc! {
                "user":       format!("u{}", i),
                "action":     "send",
                "amount":     (i as i32),
                "status":     if i % 2 == 0 { "pending" } else { "completed" },
                "createdAt":  Bson::DateTime(BsonDateTime::now()), // TTL 対象
                "continent":  "test",
            };
            let t0 = Instant::now();
            let _id = h.insert_document(&coll, doc).await?;
            mongodb::error::Result::Ok(t0.elapsed())
        }));
    }

    // ---- レイテンシ集計 ----
    let mut durs = Vec::with_capacity(n);
    for t in tasks {
        let dur = t.await.expect("task join failed")?; // ← JoinError を先に処理してから ?
        durs.push(dur);
    }
    durs.sort();

    let p50 = durs[durs.len() / 2];
    let p95 = durs[((durs.len() as f64 * 0.95) as usize).min(durs.len() - 1)];

    println!(
        "[loadtest] continent={} writes={} p50={:?} p95={:?}",
        continent, durs.len(), p50, p95
    );
    assert!(!durs.is_empty(), "no writes recorded");

    Ok(())
}
