// tests/test_rsmongodb.rs

use rsmongodb::lib_async::MongoDBAsyncHandler;
use mongodb::bson::{doc, Document};
use serde::Deserialize;
use std::{collections::HashMap, fs};
use std::sync::Arc;
use tokio::{spawn, time::{sleep, Duration}};
use mongodb::error::Error; // for custom error

/// ヘルパー関数: DB名を生成する
/// ここでは、location（大陸名-国名-県・地域名-市区町村名）の最終要素（市区町村名）を抽出し、
/// それに "_complete" を付与する（例: "southamerica-arg-buenosaires-buenosaires" → "buenosaires_complete"）
fn db_name_for(location: &str) -> String {
    let parts: Vec<&str> = location.split('-').collect();
    let city = parts.last().unwrap_or(&location);
    format!("{}_complete", city)
}

/// 既存テスト: test_mongodb_operations を残す
#[tokio::test]
async fn test_mongodb_operations() {
    let uri = "mongodb+srv://satoshi:greg1024@cluster0.sy70d.mongodb.net/test_data?retryWrites=true&w=majority";
    let database_name = "test_data";
    let collection_name = "transactions";

    let db_handler = MongoDBAsyncHandler::new(uri, database_name)
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
        .find_document::<Document>(collection_name, query.clone())
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
        .list_documents::<Document>(collection_name)
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

// -----------------------------------------------------------------------------
// Atlas JSON 用
// -----------------------------------------------------------------------------
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

// -----------------------------------------------------------------------------
// ハンドラーキャッシュ
// -----------------------------------------------------------------------------
type HandlerMap = HashMap<String, Arc<MongoDBAsyncHandler>>;

// -----------------------------------------------------------------------------
// 新しいテスト: DAG シナリオ
// -----------------------------------------------------------------------------
#[tokio::test]
async fn test_dag_scenario() {
    println!("=== Starting test_dag_scenario (DAG-based transaction test) ===");

    // 1) 大陸用 JSON を読み込む
    let config_path_continent = r"D:\city_chain_project\network\DB\config\mongodb_config\main_chain\continental_mongodb_config\mongodb_continental.json";
    let config_str_continent = fs::read_to_string(config_path_continent)
        .expect("Failed to read continent config JSON");
    let config_continent: MongodbConfig = serde_json::from_str(&config_str_continent)
        .expect("Failed to parse continent config JSON");

    // 2) 市町村用 JSON を読み込む
    let config_path_municipal = r"D:\city_chain_project\network\DB\config\mongodb_config\main_chain\municipal_mongodb_config\mongodb_municipal.json";
    let config_str_municipal = fs::read_to_string(config_path_municipal)
        .expect("Failed to read municipal config JSON");
    let config_municipal: MunicipalConfig = serde_json::from_str(&config_str_municipal)
        .expect("Failed to parse municipal config JSON");

    // 3) ハンドラー生成（順次処理でディレイを入れて負荷を下げる）
    println!("Preparing all HandlerMap for continents & municipalities...");
    let handler_map = Arc::new(prepare_handler_map(&config_continent, &config_municipal).await);

    // 4) 3つのトランザクション例
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

    // 結果待ち
    let res1 = t1.await.expect("Tx1 join error");
    let res2 = t2.await.expect("Tx2 join error");
    let res3 = t3.await.expect("Tx3 join error");

    assert!(res1.is_ok(), "Tx1 writing failed: {:?}", res1.err());
    assert!(res2.is_ok(), "Tx2 writing failed: {:?}", res2.err());
    assert!(res3.is_ok(), "Tx3 writing failed: {:?}", res3.err());

    println!("All 3 DAG transactions completed successfully.");
}

// -----------------------------------------------------------------------------
// 事前に各 URI -> Handler を順次用意する関数（負荷低減のためディレイを入れる）
// -----------------------------------------------------------------------------
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

    // 大陸用ハンドラーを順次作成
    for (name, uri) in continent_pairs {
        let db_name = db_name_for(name);
        println!("Creating continent handler: {} => {} (db: {})", name, uri, db_name);
        let handler = MongoDBAsyncHandler::new(uri, &db_name)
            .await
            .expect(&format!("Failed to create continent handler for {}", name));
        map.insert(name.to_string(), Arc::new(handler));
        sleep(Duration::from_millis(50)).await;
    }

    // 市町村用ハンドラーを順次作成
    let municipal_obj = &config_municipal.complete;
    if let Some(obj) = municipal_obj.as_object() {
        for (loc_key, val) in obj {
            println!("Creating handler for municipal key: {}", loc_key);
            if let Some(uri) = val.as_str() {
                // ここでは loc_key のうち、最後の要素（市区町村名）のみを使う
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

// -----------------------------------------------------------------------------
// 1つのトランザクションを 大陸 & 市町村 に書き込む関数
// -----------------------------------------------------------------------------
async fn handle_tx_in_parallel(
    tx: Document,
    handler_map: Arc<HandlerMap>,
) -> mongodb::error::Result<()> {
    // 1) sender_city, receiver_city を取得
    let sender_city = tx.get_str("sender_city").unwrap().to_string();
    let receiver_city = tx.get_str("receiver_city").unwrap().to_string();

    // 2) sender_continent, receiver_continent を取得 (例: "asia-japan-ishikawa-kanazawa" -> "asia")
    fn get_continent(location: &str) -> &str {
        location.split('-').next().unwrap_or("unknown")
    }
    let sender_continent = get_continent(&sender_city).to_string();
    let receiver_continent = get_continent(&receiver_city).to_string();

    let collection_name = "transactions";

    // 3) 4つのタスクを並列実行（各タスクで tx をクローン）
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

    // 4) 結果を待ち合わせ
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
