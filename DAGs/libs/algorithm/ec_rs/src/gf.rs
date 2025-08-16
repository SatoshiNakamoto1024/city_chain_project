// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\gf.rs
//! GF(2⁸) 演算（exp/log 方式）
//! 8-bit 係数なので u8 で実装。once_cell で静的テーブル。

use once_cell::sync::Lazy;

const PRIM: u16 = 0x11d; // x⁸ + x⁴ + x³ + x² + 1

static EXP: Lazy<[u8; 512]> = Lazy::new(|| {
    let mut exp = [0u8; 512];
    let mut x = 1u16;
    for i in 0..255 {
        exp[i] = x as u8;
        x <<= 1;
        if x & 0x100 != 0 {
            x ^= PRIM;
        }
    }
    for i in 255..512 {
        exp[i] = exp[i - 255];
    }
    exp
});

static LOG: Lazy<[u8; 256]> = Lazy::new(|| {
    let mut log = [0u8; 256];
    for (i, &v) in EXP.iter().enumerate().take(255) {
        log[v as usize] = i as u8;
    }
    log
});

pub struct GF256;

impl GF256 {
    #[inline] pub fn add(a: u8, b: u8) -> u8 { a ^ b }
    #[inline] pub fn sub(a: u8, b: u8) -> u8 { a ^ b }

    #[inline]
    pub fn mul(a: u8, b: u8) -> u8 {
        if a == 0 || b == 0 { 0 }
        else {
            let idx = LOG[a as usize] as usize + LOG[b as usize] as usize;
            EXP[idx]
        }
    }

    #[inline]
    pub fn inv(a: u8) -> u8 {
        assert!(a != 0, "GF256 inv(0)");
        EXP[255 - LOG[a as usize] as usize]
    }

    #[inline]
    pub fn div(a: u8, b: u8) -> u8 {
        if a == 0 { 0 } else { Self::mul(a, Self::inv(b)) }
    }
}
