// D:\city_chain_project\network\DB\mongodb\rsmongo\src/lib_async.rs

use mongodb::{
    bson::{self, doc},
    error::Result,
    options::{
        ClientOptions,
        ReadPreference,
        ReadPreferenceOptions,
        SelectionCriteria,
    },
    Client, Database, Collection,
};
use serde::de::DeserializeOwned;
use serde::Serialize;
use futures::stream::TryStreamExt;
use tokio::time::{sleep, Duration};
use std::time::Duration as StdDuration;

/// MongoDBAsyncHandler は、非同期で MongoDB への接続と CRUD 操作を行うハンドラです。
/// v2.8.x ドライバでは ClientOptions に selection_criteria を設定することで
/// セカンダリ優先の読み取りを行います。
pub struct MongoDBAsyncHandler {
    db: Database,
}

impl MongoDBAsyncHandler {
    /// プライマリ用 (書き込み) ハンドラ
    pub async fn new(uri: &str, database_name: &str) -> Result<Self> {
        // 1) クライアントオプションを解析
        let mut client_options = ClientOptions::parse(uri)?;
        // 2) タイムアウトやプールサイズを設定
        client_options.connect_timeout = Some(StdDuration::from_secs(5));
        client_options.server_selection_timeout = Some(StdDuration::from_secs(5));
        client_options.max_pool_size = Some(100);

        // 3) selection_criteria を指定しないので、デフォルト(プライマリ)
        // 4) クライアント生成
        let client = Client::with_options(client_options)?;

        // 5) Database取得
        let db = client.database(database_name);

        Ok(MongoDBAsyncHandler { db })
    }

    /// セカンダリ優先 (読み取り) ハンドラ
    pub async fn new_with_read_preference(uri: &str, database_name: &str) -> Result<Self> {
        // 1) クライアントオプションを解析
        let mut client_options = ClientOptions::parse(uri)?;
        client_options.connect_timeout = Some(StdDuration::from_secs(5));
        client_options.server_selection_timeout = Some(StdDuration::from_secs(5));
        client_options.max_pool_size = Some(100);

        // 2) セカンダリ優先にする
        // ReadPreference::SecondaryPreferred は構造体バリアントなので { options: ... } を指定
        let read_pref = ReadPreference::SecondaryPreferred {
            options: ReadPreferenceOptions::default()
        };
        client_options.selection_criteria = Some(SelectionCriteria::ReadPreference(read_pref));

        // 3) クライアント生成
        let client = Client::with_options(client_options)?;

        // 4) Database取得
        let db = client.database(database_name);

        Ok(MongoDBAsyncHandler { db })
    }

    /// ドキュメントを挿入し、挿入された ObjectId を返します。
    pub async fn insert_document<T>(
        &self,
        collection_name: &str,
        document: T,
    ) -> Result<mongodb::bson::oid::ObjectId>
    where
        T: Serialize + Unpin,
    {
        let collection: Collection<T> = self.db.collection(collection_name);
        let result = collection.insert_one(document, None).await?;
        Ok(result
            .inserted_id
            .as_object_id()
            .expect("Failed to parse inserted_id as ObjectId"))
    }

    /// リトライ付きでドキュメントを挿入します。最大 max_retries 回まで再試行します。
    pub async fn insert_document_with_retry<T>(
        &self,
        collection_name: &str,
        document: T,
        max_retries: usize,
    ) -> Result<mongodb::bson::oid::ObjectId>
    where
        T: Serialize + Unpin + Clone,
    {
        let mut attempt = 0;
        loop {
            attempt += 1;
            match self.insert_document(collection_name, document.clone()).await {
                Ok(oid) => return Ok(oid),
                Err(e) => {
                    if attempt >= max_retries {
                        eprintln!(
                            "[insert_document_with_retry] Failed after {} attempts: {:?}",
                            attempt, e
                        );
                        return Err(e);
                    }
                    let backoff_ms = 100 * attempt as u64;
                    eprintln!(
                        "[insert_document_with_retry] Error on attempt {}. Retrying in {} ms...",
                        attempt, backoff_ms
                    );
                    sleep(Duration::from_millis(backoff_ms)).await;
                }
            }
        }
    }

    /// 指定したクエリに合致するドキュメントを 1 件取得します。
    pub async fn find_document<T>(
        &self,
        collection_name: &str,
        query: bson::Document,
    ) -> Result<Option<T>>
    where
        T: DeserializeOwned + Unpin + Send + Sync,
    {
        let collection: Collection<T> = self.db.collection(collection_name);
        collection.find_one(query, None).await
    }

    /// 指定したクエリに合致するドキュメントを更新し、更新件数を返します。
    pub async fn update_document(
        &self,
        collection_name: &str,
        query: bson::Document,
        update: bson::Document,
    ) -> Result<u64> {
        let collection: Collection<bson::Document> = self.db.collection(collection_name);
        let result = collection.update_one(query, update, None).await?;
        Ok(result.modified_count)
    }

    /// 指定したクエリに合致するドキュメントを削除し、削除件数を返します。
    pub async fn delete_document(
        &self,
        collection_name: &str,
        query: bson::Document,
    ) -> Result<u64> {
        let collection: Collection<bson::Document> = self.db.collection(collection_name);
        let result = collection.delete_one(query, None).await?;
        Ok(result.deleted_count)
    }

    /// コレクション内のすべてのドキュメントを取得し、Vec<T> として返します。
    pub async fn list_documents<T>(&self, collection_name: &str) -> Result<Vec<T>>
    where
        T: DeserializeOwned + Unpin + Send + Sync,
    {
        let collection: Collection<T> = self.db.collection(collection_name);
        let mut cursor = collection.find(None, None).await?;
        let mut docs = Vec::new();
        while let Some(doc) = cursor.try_next().await? {
            docs.push(doc);
        }
        Ok(docs)
    }
}
