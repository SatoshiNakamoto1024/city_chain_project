// \city_chain_project\network\DB\mongodb\rsmongo\tests\test_rsmongodb.rs

use rsmongodb::lib_async::MongoDBAsyncHandler;
use mongodb::bson::{doc, Document};
use serde::Deserialize;
use std::{collections::HashMap, fs};
use std::sync::Arc;
use tokio::{spawn, time::{sleep, Duration}};
use mongodb::error::Error; // for custom error

// ====== 環境切替: Atlas or local ==========================================
fn load_uri_for(continent: &str) -> String {
    let env = std::env::var("CC_ENV").unwrap_or_else(|_| "atlas".into());

    if env == "local" {
        // ローカル用 JSON
        let p = "/home/satoshi/work/city_chain_project/network/DB/config/config_json/mongodb_config.json";
        let s = std::fs::read_to_string(p).expect("read local mongodb_config.json");
        let v: serde_json::Value = serde_json::from_str(&s).expect("parse local mongodb_config.json");
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
        // Atlas用 JSON（大陸のみ）
        let p = "/home/satoshi/work/city_chain_project/network/DB/config/mongodb_config/main_chain/continental_mongodb_config/mongodb_continental.json";
        let s = std::fs::read_to_string(p).expect("read atlas mongodb_continental.json");
        let v: serde_json::Value = serde_json::from_str(&s).expect("parse atlas mongodb_continental.json");
        v["complete"][continent].as_str().unwrap().to_string()
    }
}

// ====== DB名: location の最後の要素 + "_complete" ==========================
fn db_name_for(location: &str) -> String {
    let parts: Vec<&str> = location.split('-').collect();
    let last = parts.last().unwrap_or(&location);
    format!("{}_complete", last)
}

// ====== 既存の CRUD テスト ==================================================
#[tokio::test]
async fn test_mongodb_operations() {
    let uri = load_uri_for("asia"); // 例：アジアのクラスタ/ローカルを選択
    let database_name = "test_data";
    let collection_name = "transactions";

    let db_handler = MongoDBAsyncHandler::new(&uri, database_name)
        .await
        .expect("Failed to initialize MongoDBAsyncHandler");

    // --- 1) 挿入 ---
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
    assert!(!inserted_id.to_string().is_empty(), "Inserted ID should not be empty");

    // --- 2) リトライ付き挿入 ---
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
    assert!(!inserted_id_retry.to_string().is_empty(), "Inserted ID (retry) should not be empty");

    // --- 3) 取得 ---
    let query = doc! { "user": "TestUser" };
    let found_doc = db_handler
        .find_document(collection_name, query.clone())
        .await
        .expect("Failed to execute find_document");
    assert!(found_doc.is_some(), "Document should exist");
    if let Some(d) = found_doc {
        assert_eq!(d.get_str("user").unwrap(), "TestUser");
    }

    // --- 4) 更新 ---
    let update = doc! { "$set": { "status": "completed" } };
    let updated_count = db_handler
        .update_document(collection_name, query.clone(), update)
        .await
        .expect("Failed to update document");
    assert_eq!(updated_count, 1, "Should update exactly 1 document");

    // --- 5) 一覧取得 ---
    let all_docs = db_handler
        .list_documents(collection_name)
        .await
        .expect("Failed to list documents");
    assert!(!all_docs.is_empty(), "Should have at least one document in collection");

    // --- 6) 削除 ---
    let deleted_count = db_handler
        .delete_document(collection_name, query)
        .await
        .expect("Failed to delete document");
    assert_eq!(deleted_count, 1, "Should delete exactly 1 document");

    sleep(Duration::from_millis(300)).await;
}

// ====== セカンダリ優先の読み取りテスト =====================================
#[tokio::test]
async fn test_secondary_read() -> mongodb::error::Result<()> {
    println!("=== Starting test_secondary_read ===");

    let uri = load_uri_for("asia"); // 例：アジアのクラスタ/ローカルを選択
    let database_name = "test_data";
    let collection_name = "transactions_secondary";

    let write_handler = MongoDBAsyncHandler::new(&uri, database_name).await?;
    let read_handler  = MongoDBAsyncHandler::new_with_read_preference(&uri, database_name).await?;

    let doc = doc! {
        "user": "SecondaryReadTest",
        "action": "insert",
        "status": "pending",
        "createdAt": mongodb::bson::DateTime::now(),
    };
    let inserted_id = write_handler.insert_document(collection_name, doc).await?;
    println!("[write] Inserted document ID: {:?}", inserted_id);

    let found_doc = read_handler
        .find_document(collection_name, doc! {"user": "SecondaryReadTest"})
        .await?;
    println!("[read] Found document: {:?}", found_doc);
    assert!(found_doc.is_some(), "Document should be found using secondary read");

    sleep(Duration::from_millis(200)).await;
    Ok(())
}

// ====== 大陸用 JSON 構造体（municipal は削除） =============================
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

// ハンドラーキャッシュ
type HandlerMap = HashMap<String, Arc<MongoDBAsyncHandler>>;

// ====== DAG シナリオ（大陸のみ） ==========================================
#[tokio::test]
async fn test_dag_scenario() {
    println!("=== Starting test_dag_scenario (DAG-based transaction test) ===");

    // 1) 大陸用 JSON だけを読み込む（municipal は見ない）
    let config_path_continent = "/home/satoshi/work/city_chain_project/network/DB/config/mongodb_config/main_chain/continental_mongodb_config/mongodb_continental.json";
    let config_str_continent = fs::read_to_string(config_path_continent)
        .expect("Failed to read continent config JSON");
    let config_continent: MongodbConfig = serde_json::from_str(&config_str_continent)
        .expect("Failed to parse continent config JSON");

    println!("Preparing HandlerMap for continents only...");
    let handler_map = Arc::new(prepare_handler_map_continent_only(&config_continent).await);

    let tx1 = doc! {
        "sender": "A",
        "sender_city": "asia-japan-ishikawa-kanazawa",
        "amount": 200,
        "token": "harmony",
        "content": "Lv2:協力する",
        "receiver": "B",
        "receiver_city": "europe-ireland-connacht-sligo",
        "status": "completed",
        "transaction_id": "tx1",
        "createdAt": mongodb::bson::DateTime::now(),
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
        "transaction_id": "tx2",
        "createdAt": mongodb::bson::DateTime::now(),
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
        "transaction_id": "tx3",
        "createdAt": mongodb::bson::DateTime::now(),
    };

    println!("DAG: holding transactions for 1 second...");
    sleep(Duration::from_secs(1)).await;

    println!("Now writing 3 transactions in parallel (continents only)...");
    let hm = Arc::clone(&handler_map);
    let t1 = spawn(handle_tx_continent_only(tx1, hm.clone()));
    let hm = Arc::clone(&handler_map);
    let t2 = spawn(handle_tx_continent_only(tx2, hm.clone()));
    let hm = Arc::clone(&handler_map);
    let t3 = spawn(handle_tx_continent_only(tx3, hm.clone()));

    let res1 = t1.await.expect("Tx1 join error");
    let res2 = t2.await.expect("Tx2 join error");
    let res3 = t3.await.expect("Tx3 join error");

    assert!(res1.is_ok(), "Tx1 writing failed: {:?}", res1.err());
    assert!(res2.is_ok(), "Tx2 writing failed: {:?}", res2.err());
    assert!(res3.is_ok(), "Tx3 writing failed: {:?}", res3.err());

    println!("All 3 DAG transactions (continents only) completed successfully.");
}

// 大陸だけの HandlerMap を用意（ウォームアップ付き）
// 大陸だけの HandlerMap を用意
async fn prepare_handler_map_continent_only(
    config_continent: &MongodbConfig,
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

        // TTLを作成（存在すればno-op）
        let coll = handler.db().collection::<mongodb::bson::Document>("transactions");
        rsmongodb::lib_async::ensure_ttl_6months(&coll)
            .await
            .expect("ensure_ttl_6months failed");

        map.insert(name.to_string(), Arc::new(handler));
        sleep(Duration::from_millis(50)).await;
    }

    // トポロジ発見のウォームアップ（軽く待つ）
    sleep(Duration::from_millis(800)).await;

    map
}

// 1トランザクションを「送信者大陸」「受信者大陸」へ非同期書き込み（市町村は書かない）
async fn handle_tx_continent_only(
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

    // 送受それぞれで「直前 ping → 挿入」をやるタスクを作る
    async fn ping_then_insert(
        handler: Arc<MongoDBAsyncHandler>,
        coll: &'static str,
        mut doc: Document,
    ) -> mongodb::error::Result<mongodb::bson::oid::ObjectId> {
        // 1) 直前 ping（最大5回、100ms刻み）
        for _ in 0..5 {
            match handler.db().run_command(doc! {"ping": 1}, None).await {
                Ok(_) => break,
                Err(e) => {
                    // ServerSelection のときだけ少し待って再試行
                    if e.kind.to_string().contains("ServerSelection") {
                        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                        continue;
                    } else {
                        // それ以外は即エラー
                        return Err(e);
                    }
                }
            }
        }
        // createdAt が無ければ補完
        if !doc.contains_key("createdAt") {
            doc.insert("createdAt", mongodb::bson::DateTime::now());
        }
        // 2) 挿入（リトライ回数を少し増やす）
        handler.insert_document_with_retry(coll, doc, 20).await
    }

    // 送信者大陸
    let tx_sc = tx.clone();
    let sc_handler = Arc::clone(
        handler_map.get(&sender_continent)
            .ok_or_else(|| Error::custom(format!("No sender continent: {}", sender_continent)))?
    );
    let sc_task = spawn(async move {
        ping_then_insert(sc_handler, "transactions", tx_sc).await
    });

    // 受信者大陸
    let tx_rc = tx.clone();
    let rc_handler = Arc::clone(
        handler_map.get(&receiver_continent)
            .ok_or_else(|| Error::custom(format!("No receiver continent: {}", receiver_continent)))?
    );
    let rc_task = spawn(async move {
        ping_then_insert(rc_handler, "transactions", tx_rc).await
    });

    // join
    let sc_res = sc_task.await.map_err(|_| Error::custom("SenderContinent join error"))??;
    let rc_res = rc_task.await.map_err(|_| Error::custom("ReceiverContinent join error"))??;

    println!("Tx inserted => SC:{:?}, RC:{:?}", sc_res, rc_res);
    Ok(())
}
