// src/lib_async.rs

use mongodb::{
    bson::{self, doc},
    error::Result,
    options::{
        ClientOptions,
        DatabaseOptions,
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
/// v2.8.x ではクライアントオプションでの read_preference が使えないため、
/// DatabaseOptions の selection_criteria でセカンダリ優先を設定しています。
pub struct MongoDBAsyncHandler {
    db: Database,
}

impl MongoDBAsyncHandler {
    /// プライマリへの書き込み用ハンドラを生成します。
    pub async fn new(uri: &str, database_name: &str) -> Result<Self> {
        let mut client_options = ClientOptions::parse(uri)?;
        client_options.connect_timeout = Some(StdDuration::from_secs(5));
        client_options.server_selection_timeout = Some(StdDuration::from_secs(5));
        client_options.max_pool_size = Some(100);

        let client = Client::with_options(client_options)?;
        // デフォルト: プライマリ
        let db = client.database(database_name);

        Ok(MongoDBAsyncHandler { db })
    }

    /// 読み取り専用ハンドラを生成し、セカンダリ優先で読み取りを行います。
    pub async fn new_with_read_preference(uri: &str, database_name: &str) -> Result<Self> {
        let mut client_options = ClientOptions::parse(uri)?;
        client_options.connect_timeout = Some(StdDuration::from_secs(5));
        client_options.server_selection_timeout = Some(StdDuration::from_secs(5));
        client_options.max_pool_size = Some(100);

        let client = Client::with_options(client_options)?;

        // DatabaseOptions に対して、selection_criteria を設定する
        let mut db_options = DatabaseOptions::default();
        db_options.selection_criteria = Some(SelectionCriteria::ReadPreference(
            ReadPreference::SecondaryPreferred(ReadPreferenceOptions::default())
        ));

        // Database を options付きで取得
        let db = client.database_with_options(database_name, db_options);

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
