// \city_chain_project\network/DB/mongodb/rsmongo/tests/ttl_smoke.rs

use rsmongodb::lib_async::{MongoDBAsyncHandler, ensure_ttl_6months};
use mongodb::bson::doc;
use futures::TryStreamExt; // list_indexes() のカーソル用

/// Atlas 用の URI を config JSON から読む（大陸は env で切替可能）
fn load_uri_for(continent: &str) -> String {
    // 既存の大陸 JSON を使う
    let p = "/home/satoshi/work/city_chain_project/network/DB/config/mongodb_config/main_chain/continental_mongodb_config/mongodb_continental.json";
    let s = std::fs::read_to_string(p).expect("read atlas mongodb_continental.json");
    let v: serde_json::Value = serde_json::from_str(&s).expect("parse atlas mongodb_continental.json");
    v["complete"][continent]
        .as_str()
        .unwrap_or_else(|| panic!("continent '{}' not found in config", continent))
        .to_string()
}

#[tokio::test]
#[ignore] // 明示的に --ignored で実行してください
async fn ttl_index_exists_smoke() -> mongodb::error::Result<()> {
    // 環境変数で大陸／DB／コレクションを切替可能に
    let continent = std::env::var("MONGODB_CONTINENT").unwrap_or_else(|_| "asia".to_string());
    let dbname    = std::env::var("MONGODB_DB").unwrap_or_else(|_| "city_chain".to_string());
    let coll_name = std::env::var("MONGODB_COLL").unwrap_or_else(|_| "transactions".to_string());

    let uri = load_uri_for(&continent);

    // ハンドラ作成
    let handler = MongoDBAsyncHandler::new(&uri, &dbname).await?;
    let coll = handler.db().collection::<mongodb::bson::Document>(&coll_name);

    // TTL インデックス作成（存在すれば no-op）
    ensure_ttl_6months(&coll).await?;

    // インデックス一覧から ttl_createdAt_6m があるか確認
    let mut found = false;
    let mut cursor = coll.list_indexes(None).await?;
    while let Some(idx) = cursor.try_next().await? {
        if let Some(name) = idx.options.and_then(|o| o.name) {
            if name == "ttl_createdAt_6m" {
                // キーに createdAt: 1 が含まれていることも軽く確認
                if idx.keys.get("createdAt").and_then(|b| b.as_i32()).unwrap_or(0) == 1 {
                    found = true;
                    break;
                }
            }
        }
    }

    assert!(found, "TTL index 'ttl_createdAt_6m' not found on collection '{}.{}'", dbname, coll_name);
    println!("[ttl_smoke] OK: ttl_createdAt_6m exists on {}.{}", dbname, coll_name);

    Ok(())
}
