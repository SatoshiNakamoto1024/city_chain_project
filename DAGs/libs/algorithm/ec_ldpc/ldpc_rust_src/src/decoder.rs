// D:\city_chain_project\Algorithm\EC\ec_rust_src\core\ldpc\src\decoder.rs
//! LDPC Decoder: delegates to Reed–Solomon for reconstruction

use crate::{ErasureCoder, ECError};
use reed_solomon_erasure::galois_8::ReedSolomon;

pub struct LDPCDecoder;

impl LDPCDecoder {
    pub fn new() -> Self {
        LDPCDecoder
    }
}

impl ErasureCoder for LDPCDecoder {
    fn encode(
        &self,
        _data: &[u8],
        _k: usize,
        _m: usize,
    ) -> Result<Vec<Vec<u8>>, ECError> {
        Err(ECError::Encode("Use LDPCEncoder for encoding".into()))
    }

    fn decode(
        &self,
        shards: Vec<Option<Vec<u8>>>,
        k: usize,
        m: usize,
    ) -> Result<Vec<u8>, ECError> {
        // 1. RS インスタンス
        let rs = ReedSolomon::new(k, m)
            .map_err(|e| ECError::Decode(format!("RS::new: {e}")))?;

        // 2. Option<Vec<u8>> → Option<Box<[u8]>> に所有権を移す
        let mut owned: Vec<Option<Box<[u8]>>> = shards
            .into_iter()
            .map(|opt| opt.map(Vec::into_boxed_slice))
            .collect();

        // 3. 欠損復元
        rs.reconstruct(&mut owned)
            .map_err(|e| ECError::Decode(format!("RS reconstruct: {e}")))?;

        // 4. k 個のデータシャードを連結
        let mut out = Vec::new();
        for slot in owned.into_iter().take(k) {
            let slice = slot.ok_or_else(|| {
                ECError::Decode("Shard still missing after reconstruction".into())
            })?;
            out.extend_from_slice(&slice);
        }
        Ok(out)
    }
}
