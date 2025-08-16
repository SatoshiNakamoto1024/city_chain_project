// app/src/main/java/com/example/test100mb/pqc/DilithiumSigner.kt
package com.example.test100mb.pqc

import android.util.Log

/**
 * Dilithium 署名ユーティリティ（JNI 実装が必須）
 */
object DilithiumSigner {

    private const val TAG = "DilithiumSigner"

    init {
        try {
            // ① Rust でビルドした新しい .so
            System.loadLibrary("dilithium_Android_ClientCert")
            // ② 以前から使っている .so（NTRU など他で必要なら残す）
            System.loadLibrary("pqc_native")
            Log.i(TAG, "JNI signer loaded ✓")
        } catch (e: UnsatisfiedLinkError) {
            Log.e(TAG, "JNI signer not found: ${e.message}")
            throw RuntimeException("Native libraries are required but missing.", e)
        }
    }

    /**
     * 生の Dilithium 秘密鍵で署名（JNI 使用）
     * @param msg メッセージ本文（署名対象）
     * @param sk base64 decode 済みの秘密鍵（raw binary）
     * @return 署名済みメッセージ（SignedMessage 形式）、失敗時は null
     */
    fun sign(msg: ByteArray, sk: ByteArray): ByteArray? = try {
        DilithiumNative.sign(msg, sk)
    } catch (e: Exception) {
        Log.e(TAG, "sign() failed: ${e.message}", e)
        null
    }

    /** JNI ラッパー（libpqc_native.so による実装） */
    private object DilithiumNative {
        @JvmStatic
        external fun sign(msg: ByteArray, sk: ByteArray): ByteArray
    }
}
