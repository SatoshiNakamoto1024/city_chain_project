// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\fountain.rs
//! Fountain Code (RaptorQ 等) 今後実装予定

use crate::ECConfig;
use crate::core::{ErasureCoder, ECError};

/// TODO: Fountain Code 実装を追加
pub struct FountainCoder;

impl ErasureCoder for FountainCoder {
    fn encode(&self, _data: &[u8], _cfg: &ECConfig) -> Result<Vec<Vec<u8>>, ECError> {
        Err(ECError::Algo("Fountain encoder not implemented".into()))
    }

    fn decode(
        &self,
        _shards: Vec<Option<Vec<u8>>>,
        _cfg: &ECConfig,
    ) -> Result<Vec<u8>, ECError> {
        Err(ECError::Algo("Fountain decoder not implemented".into()))
    }
}
