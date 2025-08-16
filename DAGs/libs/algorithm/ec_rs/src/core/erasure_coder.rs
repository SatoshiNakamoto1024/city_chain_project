// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\erasure_coder.rs
//! プラグイン型 Erasure Coder の共通トレイト定義

use crate::ECConfig;
use thiserror::Error;

/// EC 全体で扱うエラー
#[derive(Debug, Error)]
pub enum ECError {
    #[error("I/O Error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Algorithm error: {0}")]
    Algo(String),
}

/// プラグイン実装は全てこのトレイトを実装する
pub trait ErasureCoder {
    /// data を encode して k+m 個のシャードを返す
    fn encode(&self, data: &[u8], cfg: &ECConfig) -> Result<Vec<Vec<u8>>, ECError>;

    /// Vec<Option<Vec<u8>>>（None は欠損シャード）から復元し、元データを返す
    fn decode(
        &self,
        shards: Vec<Option<Vec<u8>>>,
        cfg: &ECConfig,
    ) -> Result<Vec<u8>, ECError>;
}
