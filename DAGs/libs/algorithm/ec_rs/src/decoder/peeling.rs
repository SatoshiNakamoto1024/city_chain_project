// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\decoder\peeling.rs
//! Erasure-only Peeling Decoder  (高速 O(n))

use crate::{
    ErasureCoder, ECError,
    gf::GF256,
    design::qcpeg::SparseMatrix,
};
use rayon::prelude::*;

pub struct PeelingDecoder {
    h: SparseMatrix,
    k: usize,
    m: usize,
}

impl PeelingDecoder {
    pub fn new(h: SparseMatrix, k: usize, m: usize) -> Self {
        PeelingDecoder { h, k, m }
    }
}

impl ErasureCoder for PeelingDecoder {
    fn encode(&self, _: &[u8], _: usize, _: usize) -> Vec<Vec<u8>> {
        unreachable!("peeling decoder cannot encode")
    }

    /// shards = k+m, None=欠損
    fn decode(
        &self,
        mut shards: Vec<Option<Vec<u8>>>,
        k: usize,
        m: usize,
    ) -> Result<Vec<u8>, ECError> {

        let shard_len = shards.iter().find_map(|o| o.as_ref()).unwrap().len();
        let mut unknown = (0..k+m).filter(|i| shards[*i].is_none()).collect::<Vec<_>>();

        let mut iterations = 0;
        while !unknown.is_empty() && iterations < m {
            iterations += 1;
            let before = unknown.len();

            unknown.retain(|&u| {
                // 行 r に未知が1つだけ → 求まる
                for (r, row) in self.h.iter().enumerate() {
                    if !row.iter().any(|&(c, _)| c == u) { continue; }
                    let mut cnt_unknown = 0;
                    let mut sum = vec![0u8; shard_len];

                    for &(col, coef) in row {
                        match &shards[col] {
                            Some(buf) => {
                                for (s, &b) in sum.iter_mut().zip(buf) {
                                    *s = GF256::add(*s, GF256::mul(coef, b));
                                }
                            }
                            None => cnt_unknown += 1,
                        }
                    }

                    if cnt_unknown == 1 {
                        // この行で未知は u だけ
                        let inv = 1; // coef==1 by QC-PEG 生成
                        let mut res = sum;
                        for b in &mut res { *b = GF256::mul(*b, inv); }
                        shards[u] = Some(res);
                        return false; // solved, remove from unknown
                    }
                }
                true // still unknown
            });

            if before == unknown.len() {
                return Err(ECError::Decode("Peeling stalled – 収束せず".into()));
            }
        }

        if unknown.is_empty() {
            let mut out = Vec::new();
            for i in 0..k {
                out.extend_from_slice(shards[i].as_ref().unwrap());
            }
            Ok(out)
        } else {
            Err(ECError::Decode("Peeling failed".into()))
        }
    }
}
