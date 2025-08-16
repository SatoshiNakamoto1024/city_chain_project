// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\core\ldpc\src\pipeline\src\util.rs
//! 共有ユーティリティ: CRC32C / BLAKE3 / バッファプールなど
use once_cell::sync::Lazy;
use bytes::{Bytes, BytesMut};
use crc32c::crc32c;
use blake3::Hasher;
use tokio::sync::Mutex;
use std::collections::VecDeque;

/// 64 本までリユース出来る固定 1 MiB バッファプール
static BUF_POOL: Lazy<Mutex<VecDeque<BytesMut>>> =
    Lazy::new(|| Mutex::new(VecDeque::with_capacity(64)));

/// プールから 1 MiB 確保
pub async fn get_buf() -> BytesMut {
    let mut pool = BUF_POOL.lock().await;
    pool.pop_front().unwrap_or_else(|| BytesMut::with_capacity(1 << 20))
}

/// 使用後に返却
pub async fn put_buf(mut buf: BytesMut) {
    buf.clear();
    let mut pool = BUF_POOL.lock().await;
    if pool.len() < 64 { pool.push_back(buf); }
}

/// payload integrity (CRC32C)
pub fn calc_crc(data: &[u8]) -> u32 { crc32c(data) }

/// 強力ハッシュ (blake3)  — オブジェクト ID 生成などに利用
pub fn blake3_hash(data: &[u8]) -> [u8; 32] {
    let mut hasher = Hasher::new();
    hasher.update(data);
    *hasher.finalize().as_bytes()
}
