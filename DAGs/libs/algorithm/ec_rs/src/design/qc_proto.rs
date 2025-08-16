// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\design\qc_proto.rs
//! Protograph → QC 拡張
//! protograph を JSON/YAML で与え、lift_size (=circulant) だけ指定すれば
//! Kronecker 展開で QC 行列を返す。

use serde::Deserialize;
// use crate::gf::GF256;

#[derive(Debug, Deserialize)]
pub struct Proto {
    pub base: Vec<Vec<Option<u8>>>, // None = 0, Some(val)=係数
}

impl Proto {
    pub fn lift(&self, z: usize) -> Vec<Vec<u8>> {
        let rows = self.base.len() * z;
        let cols = self.base[0].len() * z;
        let mut h = vec![vec![0u8; cols]; rows];

        for (br, brow) in self.base.iter().enumerate() {
            for (bc, &coef) in brow.iter().enumerate() {
                if let Some(c) = coef {
                    // shift = c % z
                    let shift = (c as usize) % z;
                    for i in 0..z {
                        let r = br * z + i;
                        let c = bc * z + (i + shift) % z;
                        h[r][c] = 1;          // 係数 1 固定 (GF add)
                    }
                }
            }
        }
        h.iter_mut().for_each(|row| row.shrink_to_fit());
        h
    }
}
