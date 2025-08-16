pub mod immudb {
    tonic::include_proto!("immudb");
}

// 通常のモジュール読み込み
mod immudb_client; 
// ここで re-export (= 再エクスポート) する
// これにより `ImmuDBClient` が crate ルート (`crate::ImmuDBClient`) から見える
pub use immudb_client::ImmuDBClient;
