// src/bin/main_rsmongodb.rs

use rsmongodb::lib_async::MongoDBAsyncHandler;
use mongodb::bson::{doc, Document};
use std::sync::Arc;
use tokio::{spawn, time::{sleep, Duration}};

#[tokio::main]
async fn main() -> mongodb::error::Result<()> {
    // MongoDB Atlas の接続文字列 (ユーザー: satoshi, パスワード: greg1024)
    let uri = "mongodb+srv://satoshi:greg1024@cluster0.sy70d.mongodb.net/test_data?retryWrites=true&w=majority";
    let database_name = "test_data";
    let collection_name = "transactions";

    // 非同期ハンドラの初期化
    let db_handler = MongoDBAsyncHandler::new(uri, database_name).await?;
    // Arc でラップして所有権を共有
    let db_handler = Arc::new(db_handler);

    // 1) 単一ドキュメントの挿入（リトライなし）
    let doc_single = doc! {
        "user": "Alice",
        "action": "send",
        "amount": 100,
        "status": "pending"
    };
    let inserted_id = db_handler.insert_document(collection_name, doc_single).await?;
    println!("[single insert] Inserted with ID: {:?}", inserted_id);

    // 2) リトライ付き挿入（最大3回再試行）
    let doc_retry = doc! {
        "user": "Bob",
        "action": "receive",
        "amount": 200,
        "status": "pending"
    };
    let inserted_id_retry = db_handler.insert_document_with_retry(collection_name, doc_retry, 3).await?;
    println!("[retry insert] Inserted with ID: {:?}", inserted_id_retry);

    // 3) 100件の並列挿入 (各タスクは最大5回までリトライ)
    const NUM_TASKS: usize = 100;
    let mut tasks = Vec::new();

    for i in 0..NUM_TASKS {
        let handler_clone = Arc::clone(&db_handler);
        let doc_parallel = doc! {
            "user": format!("ParallelUser{}", i),
            "action": "transfer",
            "amount": i as i32,  // usize を i32 にキャスト
            "status": "pending"
        };
        tasks.push(spawn(async move {
            // 各挿入は最大 5 回のリトライ
            handler_clone.insert_document_with_retry("transactions", doc_parallel, 5).await
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

    // 4) コレクション内の全ドキュメントを取得して件数表示
    let all_docs = db_handler.list_documents::<Document>(collection_name).await?;
    println!("Total documents in '{}': {}", collection_name, all_docs.len());

    // 少し待機してから終了（ログ確認用）
    sleep(Duration::from_secs(2)).await;
    Ok(())
}
