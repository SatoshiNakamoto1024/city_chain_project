pub mod immudb {
    tonic::include_proto!("immudb"); // immudb.proto 内の package 名に合わせる
}

// 通常のモジュール読み込み
mod immudb_client;

// 再エクスポート：これにより `crate::ImmuDBClient` でクライアントを使えるようにする
pub use immudb_client::ImmuDBClient;
