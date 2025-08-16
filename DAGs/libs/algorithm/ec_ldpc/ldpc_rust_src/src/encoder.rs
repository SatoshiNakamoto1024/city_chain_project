// D:\city_chain_project\Algorithm\EC\ec_rust_src\core\ldpc\src\encoder.rs
use crate::{ErasureCoder, ECError};
use reed_solomon_erasure::galois_8::ReedSolomon;

/// LDPC encoder (wrapper over RS)
pub struct LDPCEncoder;

impl LDPCEncoder {
    /// Create a new encoder
    pub fn new() -> Self {
        LDPCEncoder
    }
}

impl ErasureCoder for LDPCEncoder {
    fn encode(
        &self,
        data: &[u8],
        k: usize,
        m: usize,
    ) -> Result<Vec<Vec<u8>>, ECError> {
        // Initialize RS
        let rs = ReedSolomon::new(k, m)
            .map_err(|e| ECError::Encode(format!("RS::new error: {}", e)))?;
        let total = k + m;
        let shard_size = (data.len() + k - 1) / k;
        let mut shards = vec![vec![0u8; shard_size]; total];
        // Fill data shards
        for i in 0..k {
            let start = i * shard_size;
            let end = ((i + 1) * shard_size).min(data.len());
            shards[i][..end - start].copy_from_slice(&data[start..end]);
        }
        // RS parity
        let (data_slice, parity_slice) = shards.split_at_mut(k);
        let data_refs: Vec<&[u8]> = data_slice.iter().map(|v| v.as_slice()).collect();
        let mut parity_refs: Vec<&mut [u8]> = parity_slice.iter_mut().map(|v| v.as_mut()).collect();
        rs.encode_sep(&data_refs, &mut parity_refs)
            .map_err(|e| ECError::Encode(format!("RS encode_sep error: {}", e)))?;
        Ok(shards)
    }

    fn decode(
        &self,
        _shards: Vec<Option<Vec<u8>>>,
        _k: usize,
        _m: usize,
    ) -> Result<Vec<u8>, ECError> {
        Err(ECError::Decode("Use LDPCDecoder for decoding".into()))
    }
}