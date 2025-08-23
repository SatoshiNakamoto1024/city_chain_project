// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc.rs
//! LDPC 符号 (今後実装予定)

use crate::ECConfig;
use crate::core::{ErasureCoder, ECError};

/// TODO: LDPC 実装を追加
pub struct LDPCoder;

impl ErasureCoder for LDPCoder {
    fn encode(&self, _data: &[u8], _cfg: &ECConfig) -> Result<Vec<Vec<u8>>, ECError> {
        Err(ECError::Algo("LDPC encoder not implemented".into()))
    }

    fn decode(
        &self,
        _shards: Vec<Option<Vec<u8>>>,
        _cfg: &ECConfig,
    ) -> Result<Vec<u8>, ECError> {
        Err(ECError::Algo("LDPC decoder not implemented".into()))
    }
}
