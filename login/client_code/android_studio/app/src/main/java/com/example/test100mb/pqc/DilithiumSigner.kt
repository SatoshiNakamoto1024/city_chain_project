// app/src/main/java/com/example/test100mb/pqc/DilithiumSigner.kt
package com.example.test100mb.pqc

import android.util.Log

/**
 * Dilithium 署名ユーティリティ（JNI 実装が必須）
 *
 * * Rust でビルドした libdilithium_android_clientcert.so をロード
 * * “旧” libpqc_native.so が必要なら併せてロード
 *   └ どちらも見つからない場合は sign() が null を返すだけになる
 */
object DilithiumSigner {

    private const val TAG = "DilithiumSigner"

    /** ネイティブが使えるかどうか */
    private var nativeLoaded = false

    init {
        try {
            /* ① Rust 側で生成した .so
               ─ ビルド手順で決めた **正確なファイル名** と一致させること */
            System.loadLibrary("dilithium_android_clientcert")

            /* ② 旧 .so がまだ必要なら（無ければこの行を消して OK） */
            runCatching { System.loadLibrary("pqc_native") }

            nativeLoaded = true
            Log.i(TAG, "JNI libs loaded ✓")
        } catch (e: UnsatisfiedLinkError) {
            /* ライブラリが無い端末でもクラッシュさせない -- sign() が null を返すだけ */
            Log.e(TAG, "JNI lib missing: ${e.message}")
        }
    }

    /**
     * Dillithium 秘密鍵で署名を生成
     *
     * @param msg  署名対象バイト列
     * @param sk   秘密鍵（raw binary）
     * @return     署名バイト列  /  ネイティブ未ロードなら null
     */
    fun sign(msg: ByteArray, sk: ByteArray): ByteArray? {
        if (!nativeLoaded) return null           // 署名ヘッダ無しで続行
        return try {
            DilithiumNative.sign(msg, sk)
        } catch (e: Exception) {
            Log.e(TAG, "sign() failed: ${e.message}", e)
            null
        }
    }

    /** JNI ブリッジ – Rust 側で `extern "C"` にした関数 */
    private object DilithiumNative {
        @JvmStatic
        external fun sign(msg: ByteArray, sk: ByteArray): ByteArray
    }
}
