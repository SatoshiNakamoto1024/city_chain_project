//! JNI から呼び出す Dilithium-5 署名 (minimal)

use jni::objects::{JByteArray, JClass};
use jni::sys::jbyteArray;
use jni::JNIEnv;

use pqcrypto_dilithium::dilithium5::sign as pq_sign;
use pqcrypto_traits::sign::{SecretKey, SignedMessage};   // ← as_bytes() 用

#[no_mangle]
pub extern "system" fn
Java_com_example_test100mb_pqc_DilithiumSigner_00024DilithiumNative_sign(
    env:   JNIEnv,
    _cls:  JClass,
    j_msg: JByteArray,
    j_sk:  JByteArray,
) -> jbyteArray {
    /* ---- Java byte[] → Vec<u8> ---- */
    let msg = match env.convert_byte_array(j_msg) { Ok(v) => v, Err(_) => return std::ptr::null_mut() };
    let sk_bytes = match env.convert_byte_array(j_sk) { Ok(v) => v, Err(_) => return std::ptr::null_mut() };

    /* ---- SecretKey に変換 ---- */
    let sk = match SecretKey::from_bytes(&sk_bytes) { Ok(k) => k, Err(_) => return std::ptr::null_mut() };

    /* ---- 署名 ---- */
    let signed = pq_sign(&msg, &sk);            // 型注釈は不要
    let sig_bytes = signed.as_bytes();

    /* ---- Vec<u8> → Java byte[] ---- */
    match env.byte_array_from_slice(sig_bytes) {
        Ok(arr) => arr.into_raw(),              // ★ ラッパ型 → ポインタ
        Err(_)   => std::ptr::null_mut(),
    }
}


// ─────────────────────────────────────────────
// 参考: 鍵ペアを JNI で欲しい場合はこんな感じで追加できます
// （Kotlin から呼び出すなら struct → 2本の byte[] を返却など工夫要）
//
// #[no_mangle]
// pub extern "system" fn
// Java_com_example_test100mb_pqc_DilithiumSigner_00024DilithiumNative_generateKeypair(
//     env:  JNIEnv,
//     _cls: JClass,
// ) -> jbyteArray { /* keypair() を呼んで JSON で返す等 */ }
// ─────────────────────────────────────────────
