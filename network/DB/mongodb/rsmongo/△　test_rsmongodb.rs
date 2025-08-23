// \city_chain_project\network\DB\mongodb\rsmongo\tests\test_rsmongodb.rs

use rsmongodb::lib_async::MongoDBAsyncHandler;
use rsmongodb::lib_async::ensure_ttl_6months;
use mongodb::bson::DateTime as BsonDateTime;
use mongodb::bson::{doc, Document};
use mongodb::error::Error; // for custom error
use serde::Deserialize;
use std::{collections::HashMap, fs};
use std::sync::Arc;
use tokio::{spawn, time::{sleep, Duration}};


// 共通のURIローダ
fn load_uri_for(continent: &str) -> String {
    let env = std::env::var("CC_ENV").unwrap_or_else(|_| "atlas".into());

    if env == "local" {
        // ローカル用 JSON
        let p = "/home/satoshi/work/city_chain_project/network/DB/config/config_json/mongodb_config.json";
        let s = std::fs::read_to_string(p).expect("read local mongodb_config.json");
        let v: serde_json::Value = serde_json::from_str(&s).expect("parse local mongodb_config.json");
        // 例: "Asia" キーを使う（最初のJSONに合わせる）
        v["journal_entries"][match continent {
            "asia" => "Asia",
            "europe" => "Europe",
            "oceania" => "Oceania",
            "africa" => "Africa",
            "northamerica" => "NorthAmerica",
            "southamerica" => "SouthAmerica",
            "antarctica" => "Antarctica",
            _ => "Default",
        }].as_str().unwrap().to_string()
    } else {
        // Atlas用 JSON
        let p = "/home/satoshi/work/city_chain_project/network/DB/config/mongodb_config/main_chain/continental_mongodb_config/mongodb_continental.json";
        let s = std::fs::read_to_string(p).expect("read atlas mongodb_continental.json");
        let v: serde_json::Value = serde_json::from_str(&s).expect("parse atlas mongodb_continental.json");
        v["complete"][continent].as_str().unwrap().to_string()
    }
}

/// ヘルパー関数: DB名を生成する
/// ここでは、location（例: "southamerica-arg-buenosaires-buenosaires"）の最終要素のみを使い、
/// DB名は "<市区町村名>_complete" とします。
fn db_name_for(location: &str) -> String {
    let parts: Vec<&str> = location.split('-').collect();
    let city = parts.last().unwrap_or(&location);
    format!("{}_complete", city)
}

/// 既存テスト: test_mongodb_operations をそのまま残す
#[tokio::test]
async fn test_mongodb_operations() {
    let uri = load_uri_for("asia"); // 例：アジアのクラスタ/ローカルを選択
    let database_name = "test_data";
    let collection_name = "transactions";

    // 既存のプライマリ用ハンドラ
    let db_handler = MongoDBAsyncHandler::new(&uri, database_name)
        .await
        .expect("Failed to initialize MongoDBAsyncHandler");

    // --- 1) 挿入テスト ---
    let document = doc! {
        "user": "TestUser",
        "action": "send",
        "amount": 123,
        "status": "pending"
    };
    let inserted_id = db_handler
        .insert_document(collection_name, document)
        .await
        .expect("Failed to insert document");
    assert!(inserted_id.to_string().len() > 0, "Inserted ID should not be empty");

    // --- 2) リトライ付き挿入テスト ---
    let doc_retry = doc! {
        "user": "TestRetryUser",
        "action": "receive",
        "amount": 999,
        "status": "pending"
    };
    let inserted_id_retry = db_handler
        .insert_document_with_retry(collection_name, doc_retry, 3)
        .await
        .expect("Failed to insert with retry");
    assert!(inserted_id_retry.to_string().len() > 0, "Inserted ID (retry) should not be empty");

    // --- 3) 取得テスト ---
    let query = doc! { "user": "TestUser" };
    let found_doc = db_handler
        .find_document(collection_name, query.clone())
        .await
        .expect("Failed to execute find_document");
    assert!(found_doc.is_some(), "Document should exist");
    if let Some(d) = found_doc {
        assert_eq!(d.get_str("user").unwrap(), "TestUser");
    }

    // --- 4) 更新テスト ---
    let update = doc! { "$set": { "status": "completed" } };
    let updated_count = db_handler
        .update_document(collection_name, query.clone(), update)
        .await
        .expect("Failed to update document");
    assert_eq!(updated_count, 1, "Should update exactly 1 document");

    // --- 5) 一覧取得テスト ---
    let all_docs = db_handler
        .list_documents(collection_name)
        .await
        .expect("Failed to list documents");
    assert!(all_docs.len() > 0, "Should have at least one document in collection");

    // --- 6) 削除テスト ---
    let deleted_count = db_handler
        .delete_document(collection_name, query)
        .await
        .expect("Failed to delete document");
    assert_eq!(deleted_count, 1, "Should delete exactly 1 document");

    // --- 7) 短いスリープ
    sleep(Duration::from_millis(500)).await;
}

/// 新たに追加したテスト: セカンダリ優先の読み取りを検証
#[tokio::test]
async fn test_secondary_read() -> mongodb::error::Result<()> {
    println!("=== Starting test_secondary_read ===");

    let uri = load_uri_for("asia"); // 例：アジアのクラスタ/ローカルを選択
    let database_name = "test_data";
    let collection_name = "transactions_secondary";

    // 書き込み用（プライマリ）ハンドラ
    let write_handler = MongoDBAsyncHandler::new(&uri, database_name).await?;

    // 読み取り用（セカンダリ優先）ハンドラ
    let read_handler = MongoDBAsyncHandler::new_with_read_preference(&uri, database_name).await?;

    // 1) 書き込み（プライマリ）
    let doc = doc! {
        "user": "SecondaryReadTest",
        "action": "insert",
        "status": "pending"
    };
    let inserted_id = write_handler.insert_document(collection_name, doc).await?;
    println!("[write] Inserted document ID: {:?}", inserted_id);

    // 2) 読み取り（セカンダリ優先）
    //    ※ レプリケーションに多少の遅延がある場合があるので、実際のテストでは
    //       ちょっと待機するか、複数回リトライすることも考えられます。
    let found_doc = read_handler
        .find_document(collection_name, doc! {"user": "SecondaryReadTest"})
        .await?;
    println!("[read] Found document: {:?}", found_doc);
    assert!(found_doc.is_some(), "Document should be found using secondary read");

    // 少し待機して終了
    sleep(Duration::from_millis(500)).await;
    Ok(())
}

/// Atlas JSON 用
#[derive(Debug, Deserialize)]
struct CompleteConfig {
    asia: String,
    europe: String,
    oceania: String,
    africa: String,
    northamerica: String,
    southamerica: String,
    antarctica: String,
    #[serde(rename = "default")]
    def: String,
}

#[derive(Debug, Deserialize)]
struct MongodbConfig {
    complete: CompleteConfig,
}

#[derive(Debug, Deserialize)]
struct MunicipalConfig {
    complete: serde_json::Value,
}

/// ハンドラーキャッシュ
type HandlerMap = HashMap<String, Arc<MongoDBAsyncHandler>>;

/// 新しいテスト: DAG シナリオ（Replica Set 対応）
#[tokio::test]
async fn test_dag_scenario() {
    println!("=== Starting test_dag_scenario (DAG-based transaction test) ===");

    // 1) 大陸用 JSON を読み込む
    let config_path_continent = "/home/satoshi/work/city_chain_project/network/DB/config/mongodb_config/main_chain/continental_mongodb_config/mongodb_continental.json";
    let config_str_continent = fs::read_to_string(config_path_continent)
        .expect("Failed to read continent config JSON");
    let config_continent: MongodbConfig = serde_json::from_str(&config_str_continent)
        .expect("Failed to parse continent config JSON");

    // 2) 市町村用 JSON を読み込む
    let config_path_municipal = "/home/satoshi/work/city_chain_project/network/DB/config/mongodb_config/main_chain/municipal_mongodb_config/mongodb_municipal.json";
    let config_str_municipal = fs::read_to_string(config_path_municipal)
        .expect("Failed to read municipal config JSON");
    let config_municipal: MunicipalConfig = serde_json::from_str(&config_str_municipal)
        .expect("Failed to parse municipal config JSON");

    println!("Preparing all HandlerMap for continents & municipalities...");
    let handler_map = Arc::new(prepare_handler_map(&config_continent, &config_municipal).await);

    let tx1 = doc! {
        "sender": "A",
        "sender_city": "asia-japan-ishikawa-kanazawa",
        "amount": 200,
        "token": "harmony",
        "content": "Lv2:協力する",
        "receiver": "B",
        "receiver_city": "europe-ireland-connacht-sligo",
        "status": "completed",
        "transaction_id": "tx1"
    };
    let tx2 = doc! {
        "sender": "C",
        "sender_city": "oceania-australia-nsw-sydney",
        "amount": 300,
        "token": "harmony",
        "content": "Lv3:先読みする",
        "receiver": "D",
        "receiver_city": "africa-southafrica-westerncape-capetown",
        "status": "completed",
        "transaction_id": "tx2"
    };
    let tx3 = doc! {
        "sender": "E",
        "sender_city": "northamerica-usa-massachusetts-boston",
        "amount": 400,
        "token": "harmony",
        "content": "Lv4:規律を守る",
        "receiver": "F",
        "receiver_city": "southamerica-arg-buenosaires-buenosaires",
        "status": "completed",
        "transaction_id": "tx3"
    };

    println!("DAG: holding transactions for 1 second...");
    sleep(Duration::from_secs(1)).await;

    println!("Now writing 3 transactions in parallel (DAG scenario)...");
    let hm = Arc::clone(&handler_map);
    let t1 = spawn(handle_tx_in_parallel(tx1, hm.clone()));
    let hm = Arc::clone(&handler_map);
    let t2 = spawn(handle_tx_in_parallel(tx2, hm.clone()));
    let hm = Arc::clone(&handler_map);
    let t3 = spawn(handle_tx_in_parallel(tx3, hm.clone()));

    let res1 = t1.await.expect("Tx1 join error");
    let res2 = t2.await.expect("Tx2 join error");
    let res3 = t3.await.expect("Tx3 join error");

    assert!(res1.is_ok(), "Tx1 writing failed: {:?}", res1.err());
    assert!(res2.is_ok(), "Tx2 writing failed: {:?}", res2.err());
    assert!(res3.is_ok(), "Tx3 writing failed: {:?}", res3.err());

    println!("All 3 DAG transactions completed successfully.");
}

/// 事前に各 URI -> Handler を順次用意する関数（テスト用）
async fn prepare_handler_map(
    config_continent: &MongodbConfig,
    config_municipal: &MunicipalConfig,
) -> HandlerMap {
    let mut map = HashMap::new();

    let cc = &config_continent.complete;
    let continent_pairs: Vec<(&str, &str)> = vec![
        ("asia", &cc.asia),
        ("europe", &cc.europe),
        ("oceania", &cc.oceania),
        ("africa", &cc.africa),
        ("northamerica", &cc.northamerica),
        ("southamerica", &cc.southamerica),
        ("antarctica", &cc.antarctica),
    ];

    for (name, uri) in continent_pairs {
        let db_name = db_name_for(name);
        println!("Creating continent handler: {} => {} (db: {})", name, uri, db_name);
        let handler = MongoDBAsyncHandler::new(uri, &db_name)
            .await
            .expect(&format!("Failed to create continent handler for {}", name));
        map.insert(name.to_string(), Arc::new(handler));
        sleep(Duration::from_millis(50)).await;
    }

    let municipal_obj = &config_municipal.complete;
    if let Some(obj) = municipal_obj.as_object() {
        for (loc_key, val) in obj {
            println!("Creating handler for municipal key: {}", loc_key);
            if let Some(uri) = val.as_str() {
                let db_name = db_name_for(loc_key);
                println!(" -> URI={}, db: {}", uri, db_name);
                let handler = MongoDBAsyncHandler::new(uri, &db_name)
                    .await
                    .expect(&format!("Failed to create municipal handler for {}", loc_key));
                map.insert(loc_key.clone(), Arc::new(handler));
                println!(" -> Successfully inserted handler for {}", loc_key);
                sleep(Duration::from_millis(50)).await;
            }
        }
    }

    map
}

/// 1つのトランザクションを 大陸 & 市町村 に書き込む関数
async fn handle_tx_in_parallel(
    tx: Document,
    handler_map: Arc<HandlerMap>,
) -> mongodb::error::Result<()> {
    let sender_city = tx.get_str("sender_city").unwrap().to_string();
    let receiver_city = tx.get_str("receiver_city").unwrap().to_string();

    fn get_continent(location: &str) -> &str {
        location.split('-').next().unwrap_or("unknown")
    }
    let sender_continent = get_continent(&sender_city).to_string();
    let receiver_continent = get_continent(&receiver_city).to_string();

    let collection_name = "transactions";

    let tx_sc = tx.clone();
    let sc_handler = Arc::clone(
        handler_map.get(&sender_continent)
            .ok_or_else(|| Error::custom(format!("No sender continent: {}", sender_continent)))?
    );
    let sc_task = spawn(async move {
        sc_handler.insert_document(collection_name, tx_sc).await
    });

    let tx_rc = tx.clone();
    let rc_handler = Arc::clone(
        handler_map.get(&receiver_continent)
            .ok_or_else(|| Error::custom(format!("No receiver continent: {}", receiver_continent)))?
    );
    let rc_task = spawn(async move {
        rc_handler.insert_document(collection_name, tx_rc).await
    });

    let tx_scity = tx.clone();
    let s_city_handler = Arc::clone(
        handler_map.get(&sender_city)
            .ok_or_else(|| Error::custom(format!("No sender city: {}", sender_city)))?
    );
    let s_city_task = spawn(async move {
        s_city_handler.insert_document(collection_name, tx_scity).await
    });

    let tx_rcity = tx.clone();
    let r_city_handler = Arc::clone(
        handler_map.get(&receiver_city)
            .ok_or_else(|| Error::custom(format!("No receiver city: {}", receiver_city)))?
    );
    let r_city_task = spawn(async move {
        r_city_handler.insert_document(collection_name, tx_rcity).await
    });

    let sc_res = sc_task.await.map_err(|_| Error::custom("SenderContinent join error"))??;
    let rc_res = rc_task.await.map_err(|_| Error::custom("ReceiverContinent join error"))??;
    let s_city_res = s_city_task.await.map_err(|_| Error::custom("SenderCity join error"))??;
    let r_city_res = r_city_task.await.map_err(|_| Error::custom("ReceiverCity join error"))??;

    println!(
        "Tx inserted => SC:{:?}, RC:{:?}, SCity:{:?}, RCity:{:?}",
        sc_res, rc_res, s_city_res, r_city_res
    );

    Ok(())
}

async fn load_test_continents() {
    use std::time::Instant;
    let dbname = "city_chain";
    let coll = "transactions";
    let continents = ["asia","europe","oceania","africa","northamerica","southamerica","antarctica","default"];

    // URI読み込み（あなたのJSONローダ or env）
    let mut handlers = Vec::new();
    for c in continents {
        let uri = load_uri_for(c); // ←前回案の関数でOK
        let h = MongoDBAsyncHandler::new(&uri, dbname).await.unwrap();
        handlers.push((c.to_string(), h));
    }

    // 6ヶ月TTLを一度だけ作成
    for (_, h) in &handlers {
        let coll_ref = h.db().collection::<mongodb::bson::Document>(coll);
        ensure_ttl_6months(&coll_ref).await.unwrap();
    }

    // 1大陸あたりN並列
    const N: usize = 50;
    let mut durations = Vec::new();
    for (cname, h) in handlers {
        let mut tasks = Vec::new();
        for i in 0..N {
            let h2 = h.clone();
            let cname = cname.clone();
            tasks.push(tokio::spawn(async move {
                let mut d = doc!{
                    "sender": format!("S{}", i),
                    "receiver": format!("R{}", i),
                    "status": if i % 2 == 0 { "pending" } else { "completed" },
                    "continent": cname,
                    "createdAt": mongodb::bson::Bson::DateTime(BsonDateTime::now()),
                };
                let t0 = Instant::now();
                let _ = h2.insert_document(coll, d).await.unwrap();
                t0.elapsed()
            }));
        }
        for t in tasks { durations.push(t.await.unwrap()); }
    }

    durations.sort();
    let p50 = durations[durations.len()/2];
    let p95 = durations[(durations.len() as f64 * 0.95) as usize];
    println!("writes={} p50={:?} p95={:?}", durations.len(), p50, p95);
}