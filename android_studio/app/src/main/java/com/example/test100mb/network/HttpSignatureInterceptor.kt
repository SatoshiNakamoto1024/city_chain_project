// File: app/src/main/java/com/example/test100mb/network/HttpSignatureInterceptor.kt
package com.example.test100mb.network

import android.content.Context
import android.util.Base64
import android.util.Log
import com.example.test100mb.pqc.DilithiumSigner
import com.example.test100mb.security.DilithiumSecretKeyStore
import okhttp3.Interceptor
import okhttp3.Response
import okio.Buffer

/**
 * すべての HTTP リクエストに Dilithium 署名ヘッダーを付与する Interceptor。
 * ただし BYPASS_PATHS は除外する。
 *
 * ★ OkHttp **3.x** 用実装（url() / body() など “メソッド” でアクセス）
 */
class HttpSignatureInterceptor(private val ctx: Context) : Interceptor {

    companion object {
        /** 署名を付けないパス（前方一致） */
        private val BYPASS_PATHS = listOf(
            "/register",
            "/user/keys/update",
            "/user/login"
        )
        private const val TAG = "HttpSig"
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val req = chain.request()

        /* ---------- このパスは署名ヘッダー不要？ ---------- */
        val path = req.url().encodedPath()          // ← OkHttp 3 では () が必須
        if (BYPASS_PATHS.any { path.startsWith(it) }) {
            return chain.proceed(req)
        }

        /* ---------- Dilithium 秘密鍵をロード ---------- */
        val sk: ByteArray? = try {
            DilithiumSecretKeyStore.load(ctx)      // 例外なら null 扱い
        } catch (e: Exception) {
            null
        }
        if (sk == null) {
            Log.w(TAG, "secret-key not found – unsigned request: $path")
            return chain.proceed(req)
        }

        /* ---------- Body → byte[] ---------- */
        val bodyBytes: ByteArray = req.body()?.let { body ->
            val buf = Buffer()
            body.writeTo(buf)
            buf.readByteArray()
        } ?: ByteArray(0)

        /* ---------- 署名生成 ---------- */
        val sig = DilithiumSigner.sign(bodyBytes, sk)
        if (sig == null || sig.isEmpty()) {
            Log.w(TAG, "sign() failed; unsigned request: $path")
            return chain.proceed(req)
        }
        val b64 = Base64.encodeToString(sig, Base64.NO_WRAP)

        /* ---------- ヘッダー追加 ---------- */
        val signedReq = req.newBuilder()
            .addHeader("X-Dil-Signature", b64)
            .build()

        return chain.proceed(signedReq)
    }
}
