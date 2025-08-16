// D:\city_chain_project\Algorithm\EC\ec_rust_src\core\ldpc\src\matrix.rs
//! GF(2^8) arithmetic and parity-check matrix utilities
//!
//! Provides GaloisField operations and generates a parity-check matrix H = [A | I]

const PRIM: u16 = 0x11d; // x^8 + x^4 + x^3 + x^2 + 1

/// Galois Field GF(2^8) helper
pub struct GaloisField {
    exp: [u8; 512],
    log: [u8; 256],
}

impl GaloisField {
    /// Build exponent and log tables for GF(2^8)
    pub fn new() -> Self {
        let mut exp = [0u8; 512];
        let mut log = [0u8; 256];
        let mut x = 1u16;
        for i in 0..255 {
            exp[i] = x as u8;
            log[x as usize] = i as u8;
            x <<= 1;
            if x & 0x100 != 0 {
                x ^= PRIM;
            }
        }
        // extend exp table for easy indexing
        for i in 255..512 {
            exp[i] = exp[i - 255];
        }
        GaloisField { exp, log }
    }

    /// Addition in GF(2^8) (bitwise XOR)
    #[inline]
    pub fn add(a: u8, b: u8) -> u8 {
        a ^ b
    }

    /// Multiplication in GF(2^8)
    #[inline]
    pub fn mul(&self, a: u8, b: u8) -> u8 {
        if a == 0 || b == 0 {
            0
        } else {
            let la = self.log[a as usize] as usize;
            let lb = self.log[b as usize] as usize;
            self.exp[la + lb]
        }
    }

    /// Division in GF(2^8)
    #[inline]
    pub fn div(&self, a: u8, b: u8) -> u8 {
        if a == 0 {
            0
        } else if b == 0 {
            panic!("Division by zero in GF(2^8)");
        } else {
            let la = self.log[a as usize] as i32;
            let lb = self.log[b as usize] as i32;
            let idx = (la - lb).rem_euclid(255) as usize;
            self.exp[idx]
        }
    }

    /// Generate parity-check matrix H of size m x n over GF(2^8)
    /// Systematic LDPC: H = [A | I], where A is m x k, I is m x m identity.
    /// - `n`: total shards (k + m)
    /// - `k`: number of data shards
    /// - `m`: number of parity shards
    pub fn generate_parity_check_matrix(
        &self,
        n: usize,
        k: usize,
        m: usize,
    ) -> Vec<Vec<u8>> {
        let mut h = vec![vec![0u8; n]; m];
        // A matrix: each row r connects to data column c if (c % m) == r
        for r in 0..m {
            for c in 0..k {
                if c % m == r {
                    h[r][c] = 1;
                }
            }
            // Identity part on parity columns
            let pc = k + r;
            if pc < n {
                h[r][pc] = 1;
            }
        }
        h
    }
}
