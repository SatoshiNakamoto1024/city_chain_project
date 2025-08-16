// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\encoder\sparse_mul.rs
//! 疎行列 × シャードベクトル  (AVX2 / NEON / Fallback)
//!   parity_row ^= coef * data_col
//! Sparse-Matrix × shard-vector
//!
//! dst_row ^= coef * src_col  (GF256)
//! SIMD (AVX2 / NEON) を自動切替。フォールバックはスカラー。

use once_cell::sync::Lazy;
use rayon::prelude::*;
use crate::gf::GF256;
use crate::design::qcpeg::SparseMatrix;

//──────────────────────────────────────────────
// 256×256 乗算 LUT
//──────────────────────────────────────────────
static MUL_LUT: Lazy<[[u8; 256]; 256]> = Lazy::new(|| {
    let mut t = [[0u8; 256]; 256];
    for a in 0..256 {
        for b in 0..256 {
            t[a][b] = GF256::mul(a as u8, b as u8);
        }
    }
    t
});

//──────────────────────────────────────────────
// Fallback scalar
//──────────────────────────────────────────────
#[inline]
fn xor_mul_scalar(dst: &mut [u8], src: &[u8], coef: u8) {
    let lut = &MUL_LUT[coef as usize];
    for (d, &s) in dst.iter_mut().zip(src) {
        *d ^= lut[s as usize];
    }
}

//──────────────────────────────────────────────
// AVX2
//──────────────────────────────────────────────
#[cfg(all(target_arch = "x86_64", target_feature = "avx2"))]
mod simd_avx2 {
    use super::*;
    use core::arch::x86_64::*;

    #[inline]
    pub unsafe fn xor_mul(dst: &mut [u8], src: &[u8], coef: u8) {
        let lut = &MUL_LUT[coef as usize];
        let chunks = dst.len() / 32;
        for i in 0..chunks {
            let dptr = dst.as_mut_ptr().add(i*32) as *mut __m256i;
            let sptr = src.as_ptr().add(i*32)     as *const __m256i;

            let s = _mm256_loadu_si256(sptr);

            // nibble split
            let lo  = _mm256_and_si256(s, _mm256_set1_epi8(0x0f));
            let hi  = _mm256_and_si256(_mm256_srli_epi32(s, 4), _mm256_set1_epi8(0x0f));

            let lut_lo = _mm256_loadu_si256(lut.as_ptr()      as *const __m256i);
            let lut_hi = _mm256_loadu_si256(lut.as_ptr().add(16) as *const __m256i);

            let p0 = _mm256_shuffle_epi8(lut_lo, lo);
            let p1 = _mm256_shuffle_epi8(lut_hi, hi);

            let prod = _mm256_xor_si256(p0, p1);
            let d    = _mm256_loadu_si256(dptr);
            _mm256_storeu_si256(dptr, _mm256_xor_si256(d, prod));
        }
        xor_mul_scalar(&mut dst[chunks*32..], &src[chunks*32..], coef);
    }
}

//──────────────────────────────────────────────
// NEON
//──────────────────────────────────────────────
#[cfg(all(target_arch = "aarch64", target_feature = "neon"))]
mod simd_neon {
    use super::*;
    use core::arch::aarch64::*;

    #[inline]
    pub unsafe fn xor_mul(dst: &mut [u8], src: &[u8], coef: u8) {
        let lut = &MUL_LUT[coef as usize];
        let chunks = dst.len() / 16;
        for i in 0..chunks {
            let dptr = dst.as_mut_ptr().add(i*16);
            let sptr = src.as_ptr().add(i*16);

            let s = vld1q_u8(sptr);
            let lo = vandq_u8(s, vdupq_n_u8(0x0f));
            let hi = vshrq_n_u8(vandq_u8(s, vdupq_n_u8(0xf0)), 4);

            let lut_lo = vld1q_u8(lut.as_ptr());
            let lut_hi = vld1q_u8(lut.as_ptr().add(16));

            let p0 = vqtbl1q_u8(lut_lo, lo);
            let p1 = vqtbl1q_u8(lut_hi, hi);
            let prod = veorq_u8(p0, p1);

            let d = vld1q_u8(dptr);
            vst1q_u8(dptr, veorq_u8(d, prod));
        }
        xor_mul_scalar(&mut dst[chunks*16..], &src[chunks*16..], coef);
    }
}

//──────────────────────────────────────────────
// マルチアーキテクチャラッパー
//──────────────────────────────────────────────
#[inline]
fn xor_mul(dst: &mut [u8], src: &[u8], coef: u8) {
    #[cfg(all(target_arch="x86_64", target_feature="avx2"))]
    unsafe { return simd_avx2::xor_mul(dst, src, coef) }

    #[cfg(all(target_arch="aarch64", target_feature="neon"))]
    unsafe { return simd_neon::xor_mul(dst, src, coef) }

    xor_mul_scalar(dst, src, coef)
}

//──────────────────────────────────────────────
// public: H (m×k) × data-shards  → parity-shards
//──────────────────────────────────────────────
pub fn sparse_mul(h: &SparseMatrix, data: &[Vec<u8>]) -> Vec<Vec<u8>> {
    let shard_len = data[0].len();
    let mut out   = vec![vec![0u8; shard_len]; h.len()];

    out.par_iter_mut().enumerate().for_each(|(r, row)| {
        for &(c, coef) in &h[r] {
            xor_mul(row, &data[c], coef);
        }
    });
    out
}
