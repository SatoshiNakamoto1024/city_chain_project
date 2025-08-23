// \city_chain_project\network\DB\mongodb\rsmongo\tests\multicontinent_loadtest.rs

use futures::future::join_all;
use mongodb::bson::{doc, Bson, DateTime};
use rsmongodb::lib_async::MongoDBAsyncHandler;
use std::fs;
use std::sync::Arc;
use std::time::{Duration, Instant};

/// continental_mongodb_config から対象大陸の URI を取り出す
fn load_uri_for(continent: &str) -> String {
    let p = "/home/satoshi/work/city_chain_project/network/DB/config/mongodb_config/main_chain/continental_mongodb_config/mongodb_continental.json";
    let s = fs::read_to_string(p).expect("read mongodb_continental.json");
    let v: serde_json::Value = serde_json::from_str(&s).expect("parse mongodb_continental.json");
    v["complete"][continent]
        .as_str()
        .unwrap_or_else(|| panic!("continent '{}' not found in config", continent))
        .to_string()
}

/// 簡易 p50 / p95 計算（Duration ベクタをソートして分位点を返す）
fn p50_p95(mut durs: Vec<Duration>) -> (Duration, Duration) {
    if durs.is_empty() {
        return (Duration::from_millis(0), Duration::from_millis(0));
    }
    durs.sort_unstable();
    let p50_idx = durs.len() / 2;
    // ★ 修正: キャストに括弧を付けてから .min(...) を呼ぶ
    let p95_idx = (((durs.len() as f64) * 0.95).floor() as usize).min(durs.len() - 1);
    (durs[p50_idx], durs[p95_idx])
}

/// 大陸 1つ分の書き込み負荷（n件）を投げて、各書き込みの elapsed を返す
async fn run_load_for_continent(continent: &'static str, n: usize) -> (String, Vec<Duration>) {
    let dbname = std::env::var("MONGODB_DB").unwrap_or_else(|_| "city_chain".to_string());
    let coll = "transactions";
    let uri = load_uri_for(continent);

    // ★ 修正: Arc で包んで 'static を満たす
    let handler = Arc::new(
        MongoDBAsyncHandler::new(&uri, &dbname)
            .await
            .unwrap_or_else(|e| panic!("init handler for {} failed: {}", continent, e)),
    );

    // n 本の並列タスクを起動
    let mut tasks = Vec::with_capacity(n);
    for i in 0..n {
        let h = Arc::clone(&handler);
        tasks.push(tokio::spawn(async move {
            let d = doc! {
                "sender": format!("S{}", i),
                "receiver": format!("R{}", i),
                "amount": (i as i64) % 1000,
                "status": if i % 2 == 0 { "pending" } else { "completed" },
                "continent": continent,
                // TTL 対象の createdAt は bson::DateTime を使う
                "createdAt": Bson::DateTime(DateTime::now()),
            };
            let t0 = Instant::now();
            h.insert_document(coll, d).await.expect("insert failed");
            t0.elapsed()
        }));
    }

    // ジョインして Duration を集計
    let mut durs = Vec::with_capacity(n);
    for t in tasks {
        durs.push(t.await.expect("join error"));
    }
    (continent.to_string(), durs)
}

#[tokio::test(flavor = "multi_thread", worker_threads = 8)]
async fn multicontinent_loadtest() {
    // 対象大陸（必要に応じて増減OK）
    const CONTINENTS: &[&str] = &[
        "asia",
        "europe",
        "northamerica",
        "southamerica",
        "africa",
        "oceania",
        // "antarctica", // 使うならコメントアウト外す
    ];

    // 1大陸あたりの書き込み件数（デフォルト100、環境変数で上書き可）
    let n_per_continent: usize = std::env::var("LOAD_N")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(100);

    println!(
        "[multicontinent] continents={:?} writes/continent={} db={}",
        CONTINENTS,
        n_per_continent,
        std::env::var("MONGODB_DB").unwrap_or_else(|_| "city_chain".to_string())
    );

    // すべての大陸を同時に走らせる
    let futures = CONTINENTS
        .iter()
        .copied()
        .map(|c| run_load_for_continent(c, n_per_continent));
    let results = join_all(futures).await;

    // 大陸ごとの p50/p95 を表示
    let mut total_durs: Vec<Duration> = Vec::new();
    for (continent, durs) in results {
        let (p50, p95) = p50_p95(durs.clone());
        println!(
            "[{}] writes={} p50={:?} p95={:?}",
            continent,
            durs.len(),
            p50,
            p95
        );
        total_durs.extend(durs);
    }

    // 全体の p50/p95 も表示
    let (tp50, tp95) = p50_p95(total_durs.clone());
    println!(
        "[overall] writes={} p50={:?} p95={:?}",
        total_durs.len(),
        tp50,
        tp95
    );

    assert!(!total_durs.is_empty(), "no writes performed");
}
