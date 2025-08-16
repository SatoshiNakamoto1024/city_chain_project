// D:\city_chain_project\network\DB\mongodb\rsmongo\src/bin/main_rsmongodb.rs

use rsmongodb::lib_async::MongoDBAsyncHandler;
use mongodb::bson::{doc, Document};
use std::sync::Arc;
use tokio::{spawn, time::{sleep, Duration}};

#[tokio::main]
async fn main() -> mongodb::error::Result<()> {
    // Atlas のレプリカセット構成の接続文字列
    let uri = "mongodb+srv://satoshi:greg1024@cluster0.sy70d.mongodb.net/test_data?retryWrites=true&w=majority";
    let database_name = "test_data";
    let collection_name = "transactions";

    // 1) 書き込み用ハンドラ（プライマリ）
    let write_handler = Arc::new(MongoDBAsyncHandler::new(uri, database_name).await?);

    // 2) 読み取り用ハンドラ（セカンダリ優先）
    let read_handler = Arc::new(MongoDBAsyncHandler::new_with_read_preference(uri, database_name).await?);

    // --- (A) 単一ドキュメントをプライマリへ書き込み ---
    let doc_single = doc! {
        "user": "Alice",
        "action": "send",
        "amount": 100,
        "status": "pending"
    };
    let inserted_id = write_handler.insert_document(collection_name, doc_single).await?;
    println!("[write] Inserted with ID: {:?}", inserted_id);

    // --- (B) セカンダリ優先で読み取り ---
    let found_doc = read_handler
        .find_document::<Document>(collection_name, doc! {"user": "Alice"})
        .await?;
    println!("[read] Found document: {:?}", found_doc);

    // --- (C) 100件の並列書き込み（すべてプライマリへ書き込み）---
    const NUM_TASKS: usize = 100;
    let mut tasks = Vec::new();

    for i in 0..NUM_TASKS {
        let handler_clone = Arc::clone(&write_handler);
        let doc_parallel = doc! {
            "user": format!("ParallelUser{}", i),
            "action": "transfer",
            "amount": i as i32,
            "status": "pending"
        };
        tasks.push(spawn(async move {
            handler_clone.insert_document_with_retry(collection_name, doc_parallel, 5).await
        }));
    }

    let mut success_count = 0_usize;
    for (idx, task) in tasks.into_iter().enumerate() {
        match task.await {
            Ok(Ok(id)) => {
                success_count += 1;
                println!("[parallel insert {}] Inserted doc with ID: {:?}", idx, id);
            }
            Ok(Err(e)) => {
                eprintln!("[parallel insert {}] Insertion error: {:?}", idx, e);
            }
            Err(e) => {
                eprintln!("[parallel insert {}] Task join error: {:?}", idx, e);
            }
        }
    }
    println!("Parallel insertion completed. Success: {}/{}", success_count, NUM_TASKS);

    // --- (D) コレクション内の全ドキュメントを取得（セカンダリ優先） ---
    let all_docs = read_handler.list_documents::<Document>(collection_name).await?;
    println!("Total documents in '{}': {}", collection_name, all_docs.len());

    // 短いウェイトを入れて終了（ログ確認用）
    sleep(Duration::from_secs(2)).await;
    Ok(())
}
