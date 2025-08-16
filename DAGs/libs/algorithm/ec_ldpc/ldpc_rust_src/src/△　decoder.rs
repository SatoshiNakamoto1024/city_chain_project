// D:\city_chain_project\Algorithm\EC\ec_rust_src\core\ldpc\src\decoder.rs
//! LDPC Decoder: solves H_sub * x_missing = syndrome via Gaussian elimination

use crate::{ErasureCoder, ECError};
use crate::matrix::GaloisField;

/// LDPC decoder
pub struct LDPCDecoder {
    gf: GaloisField,
}

impl LDPCDecoder {
    pub fn new() -> Self {
        LDPCDecoder { gf: GaloisField::new() }
    }

    /// Solve linear system A x = b over GF(2^8)
    fn solve_system(
        &self,
        mut a: Vec<Vec<u8>>,
        mut b: Vec<u8>,
    ) -> Result<Vec<u8>, ECError> {
        let m = a.len();
        let n = a[0].len();
        let mut col = 0;
        for row in 0..n {
            // find pivot
            let mut piv = row;
            while piv < m && a[piv][col] == 0 {
                piv += 1;
            }
            if piv == m {
                col += 1;
                if col == n {
                    break;
                }
                continue;
            }
            a.swap(row, piv);
            b.swap(row, piv);
            // normalize row
            let inv = self.gf.div(1, a[row][col]);
            for j in col..n {
                a[row][j] = self.gf.mul(a[row][j], inv);
            }
            b[row] = self.gf.mul(b[row], inv);
            // eliminate
            for i in 0..m {
                if i != row && a[i][col] != 0 {
                    let factor = a[i][col];
                    for j in col..n {
                        a[i][j] = GaloisField::add(
                            a[i][j],
                            self.gf.mul(factor, a[row][j]),
                        );
                    }
                    b[i] = GaloisField::add(
                        b[i],
                        self.gf.mul(factor, b[row]),
                    );
                }
            }
            col += 1;
            if col == n {
                break;
            }
        }
        // extract solution
        let mut x = vec![0u8; n];
        for i in 0..n {
            x[i] = b[i];
        }
        Ok(x)
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
        let n = k + m;
        let shard_len = shards.iter()
            .filter_map(|o| o.as_ref())
            .next()
            .unwrap()
            .len();
        // build parity-check matrix
        let h = self.gf.generate_parity_check_matrix(n, k, m);

        // identify missing and present indices
        let mut missing = Vec::new();
        let mut present = Vec::new();
        for i in 0..n {
            if shards[i].is_some() {
                present.push(i);
            } else {
                missing.push(i);
            }
        }
        if missing.len() > m {
            return Err(ECError::Decode("Too many missing shards".into()));
        }

        // prepare container for recovered shards
        let mut recovered_shards = vec![vec![0u8; shard_len]; missing.len()];

        // for each byte position
        for bi in 0..shard_len {
            // compute syndrome b_vec[r]
            let mut b_vec = vec![0u8; m];
            for r in 0..m {
                let mut sum = 0u8;
                for &pi in &present {
                    sum = GaloisField::add(
                        sum,
                        self.gf.mul(
                            h[r][pi],
                            shards[pi].as_ref().unwrap()[bi],
                        ),
                    );
                }
                b_vec[r] = sum;
            }

            // build submatrix A: m x e
            let mut a_mat = vec![vec![0u8; missing.len()]; m];
            for (ci, &mi) in missing.iter().enumerate() {
                for r in 0..m {
                    a_mat[r][ci] = h[r][mi];
                }
            }

            // solve for missing symbols
            let sol = self.solve_system(a_mat, b_vec)
                .map_err(|e| ECError::Solve(e.to_string()))?;

            for (ci, &val) in sol.iter().enumerate() {
                recovered_shards[ci][bi] = val;
            }
        }

        // fill recovered shards and concatenate data shards
        let mut tmp = shards.clone();
        for (ci, &mi) in missing.iter().enumerate() {
            tmp[mi] = Some(recovered_shards[ci].clone());
        }
        let mut full = Vec::with_capacity(k * shard_len);
        for i in 0..k {
            full.extend_from_slice(tmp[i].as_ref().unwrap());
        }
        Ok(full)
    }
}
