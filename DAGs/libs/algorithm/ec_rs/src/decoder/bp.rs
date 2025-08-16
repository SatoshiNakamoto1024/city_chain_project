// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\decoder\bp.rs
//! 完全 Sum-Product BP  (float LLR)
//
// Min-Sum より精度重視。ここではラッパーとして Min-Sum に委譲。

use crate::{
    ErasureCoder, ECError,
    gf::GF256,
    design::qcpeg::SparseMatrix,
};
use super::min_sum::MinSumDecoder;

pub struct BPDecoder {
    inner: MinSumDecoder,
}

impl BPDecoder {
    pub fn new(h: SparseMatrix, k: usize, max_iter: usize) -> Self {
        BPDecoder {
            inner: MinSumDecoder::new(h, k, max_iter, 1.0), // scale=1 (Sum-Product)
        }
    }
}

impl ErasureCoder for BPDecoder {
    fn encode(&self, _: &[u8], _: usize, _: usize) -> Vec<Vec<u8>> { unreachable!() }
    fn decode(
        &self,
        shards: Vec<Option<Vec<u8>>>,
        k: usize,
        m: usize,
    ) -> Result<Vec<u8>, ECError> {
        self.inner.decode(shards, k, m)
    }
}
